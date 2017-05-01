# GoTorrent
Desarrollado por 
Adrian Gutierrez Rodriguez y 
Gerard Gonzalez Serramia

GoTorrent es un servicio que pretende emular el comportamiento de Torrent mediante el uso de protocols Gossip, implementando 3 metodos de distribucion de la información, 
que son Pull, Push y una combinacion de Pull y Push.

Para el funcionamiento del programa es necesario instalar las librerias de pyactor mediante los siguientes comandos:

git clone http://github.com/pedrotgn/pyactor

ls

cd pyactor/

python setup.py install

Una vez obtenidas las librerias de pyactor ya se puede proceder a la ejecucion de la aplicacion mediante la siguiente sintaxis:

python goTorrent.py Parametro [1 Push,  2 Pull, 3 Pull&Push] [num_peers]

Ejemplo: python goTorrent.py  1 10

Ejemplo: python goTorrent.py  2 10

Ejemplo: python goTorrent.py  3 20

gotorrent

Coverage Status codecov Code Health Build Status