fid = fopen('server_log.out');
data = fscanf(fid,'%04X%04X',[2,inf]);
data_iq = data(1,:) + 1i*data(2,:);
fclose(fid);
