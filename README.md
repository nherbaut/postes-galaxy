# postes-galaxy

Example apache2 config:

```
<VirtualHost 167.114.249.96:80>
LogFormat "%V %h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" rsslog

    LogLevel info 
    ServerAlias *.rss.nextnet.top
    ServerAlias *.html.nextnet.top
    WSGIDaemonProcess rss user=www-data group=www-data threads=1
    WSGIScriptAlias / /var/www/rss/rss.wsgi

    <Directory /var/www/rss>
        WSGIProcessGroup rss
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
CustomLog /var/log/apache2/rss.log rsslog

</VirtualHost>

```
