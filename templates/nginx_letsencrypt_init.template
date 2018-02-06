server {
    listen {{ ctx("nginx.server_ip") }}:80;
    server_name {{ ctx("nginx.server_name") }};
    location /.well-known/acme-challenge {
      root /var/www/html;
    }
}
