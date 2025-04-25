################ OS4D ##############
#### ssh nuc1
#### vi mounts/nginx/share/ssl/os4d.org/fullchain.pem mounts/nginx/share/ssl/os4d.org/privkey.pem
certbot certonly --manual --preferred-challenges=dns \
  --email g.bronzini@singlewave.co.uk \
  --server https://acme-v02.api.letsencrypt.org/directory \
  --agree-tos \
  -d *.os4d.org -d os4d.org
