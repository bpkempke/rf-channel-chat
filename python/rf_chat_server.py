# Tcp Chat server
# Initial code from: http://www.binarytides.com/code-chat-application-server-client-sockets-python/
 
import argparse
import socket, select
import struct
import numpy as np

client_num_tx = []
client_buffers = []
    
def remove_socket(sock):
    sock.close()
    which_closed = connection_list.index(sock)
    del client_num_tx[which_closed]
    del client_buffers[which_closed]
    del connection_list[which_closed]

#Function to broadcast chat messages to all connected clients
def broadcast_data (i_sample, q_sample):
    i_sample = 65536 + i_sample if i_sample < 0 else i_sample
    q_sample = 65536 + q_sample if q_sample < 0 else q_sample
    print "Sample #%d: %d, %d" % (client_num_tx[0], i_sample, q_sample)
    message = format(i_sample, '04X') + format(q_sample, '04X') + '\n'
    log_file.write(message)
    #Do not send the message to master socket and the client who has send us the message
    for socket in connection_list:
        if socket != server_socket:
            try :
                socket.send(message)
            except :
                # broken socket connection may be, chat client pressed ctrl+c for example
                remove_socket(socket)
    
 
if __name__ == "__main__":
    #One option right now: Optional datafile of complex shorts to inject
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inject-data', default=None)
    args = parser.parse_args()
     
    #Pull in injection file if specified
    injection_data = None
    injection_data_idx = 0
    if args.inject_data:
        injection_data = np.fromfile(args.inject_data, dtype=np.dtype('i2'))
 
    log_file = open("server_log.out", 'w', 0)
    log_file.truncate()
     
    # List to keep track of socket descriptors
    connection_list = []
    RECV_BUFFER = 4096 # Advisable to keep it as an exponent of 2
    PORT = 1234

    # Strategy:
    #   1: Assume everyone is running at the same sample rate
    #   2: Upon connection of a new client, set num_tx, num_rx for that client to current total
    #   3: Upon reception of data from a client, increment num_tx for that client and only broadcast the channel value if num_tx for all clients are at the same level
    agg_tx_i = 0
    agg_tx_q = 0
     
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_list = [server_socket]
    # this has no effect, why ?
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(10)
 
    # Add server socket to the list of readable connections
    #connection_list.append(server_socket)
 
    print "Chat server started on port " + str(PORT)
 
    while 1:
        # Get the list sockets which are ready to be read through select
        read_sockets,write_sockets,error_sockets = select.select(server_socket_list+connection_list,[],[])
 
        for sock in read_sockets:
            #New connection
            if sock == server_socket:
                # Handle the case in which there is a new connection recieved through server_socket
                sockfd, addr = server_socket.accept()
                connection_list.append(sockfd)
                if len(client_num_tx) > 0:
                    client_num_tx.append(max(client_num_tx))
                else:
                    client_num_tx.append(0)
                client_buffers.append("")
                print "Client (%s, %s) connected" % addr
                 
                #broadcast_data(sockfd, "[%s:%s] entered room\n" % addr)
             
            #Some incoming message from a client
            else:
                ## Data recieved from client, process it
                #try:
                    #In Windows, sometimes when a TCP program closes abruptly,
                    # a "Connection reset by peer" exception will be thrown
                    sock_idx = connection_list.index(sock)
                    data = sock.recv(RECV_BUFFER)
                    client_buffers[sock_idx] += data
                    if len(client_buffers[sock_idx]) >= 9:
                        #Pull a sample out the front of the array
                        client_num_tx[sock_idx] = client_num_tx[sock_idx] + 1
                        cur_i = int(client_buffers[sock_idx][0:4],16)
                        cur_q = int(client_buffers[sock_idx][4:8],16)
                        client_buffers[sock_idx] = client_buffers[sock_idx][9:]

                        #Add sample to the channel, currently just accounting for some path loss
                        agg_tx_i = agg_tx_i + cur_i/10
                        agg_tx_q = agg_tx_q + cur_q/10

                        ##Add some noise as well
                        #agg_tx_i = agg_tx_i + int(np.random.normal(0, 100, 1))
                        #agg_tx_q = agg_tx_q + int(np.random.normal(0, 100, 1))

                        #Add the sample to the channel and push out to everyone listening
                        if len(client_num_tx) == 1 or client_num_tx[1:] == client_num_tx[:-1]:
                            #Inject in specified signal if requested
                            if injection_data:
                                agg_tx_i += injection_data[injection_data_idx]
                                agg_tx_q += injection_data[injection_data_idx+1]
                                injection_data_idx += 2
                                if injection_data_idx >= len(injection_data):
                                    injection_data_idx = 0

                            #Push data to subscribers and reset
                            broadcast_data(agg_tx_i, agg_tx_q)
                            agg_tx_i = 0
                            agg_tx_q = 0
                 
                #except:
                #    #No longer need to let everyone know a connection has been dropped
                #    #broadcast_data(sock, "Client (%s, %s) is offline" % addr)
                #    print "Client (%s, %s) is offline" % addr
                #    remove_socket(sock)
                #    continue
     
    server_socket.close()
