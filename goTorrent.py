from pyactor.context import set_context, create_host, sleep, shutdown, interval, later
import time
import random
import sys
from pyactor.exceptions import TimeoutError
from tqdm import tqdm

push = False
pull = False

class Tracker(object):
    _tell = ['setProxys','announce','publish','publish_all','active_interval','stop_interval','garbage_cleanner','setComplet']
    _ask = ['get_peers'] 
    _ref = ['announce']
    
    def __init__(self):
        self.torrents = {}
        
    def setProxys(self,printer):
        self.printer = printer
        
    def announce(self, torrent_hash, peer):
        timestamp = time.time()
        if not self.torrents.has_key(torrent_hash):
            self.torrents[torrent_hash]={}
        self.torrents[torrent_hash][peer.id] = {}
        self.torrents[torrent_hash][peer.id]['ref']=peer
        self.torrents[torrent_hash][peer.id]['time']=timestamp
        self.torrents[torrent_hash][peer.id]['seed']=False


    def stop_interval(self):
        self.interval1.set()
    
    def active_interval(self):
        self.interval1 = interval(self.host, 15, self.proxy, "garbage_cleanner")

    def garbage_cleanner(self):
        timestamp = time.time()
        for clave in self.torrents.keys():
            for peer in self.torrents[clave].keys():
                 temp=self.torrents[clave].get(peer)
                 #print "analizando peer",peer,"de hash",clave,"tiempo",temp,"actual",timestamp
                 if (timestamp >= (temp['time'] +10) ):
                     self.torrents[clave].pop(peer)
                     msg_temp = "Eliminado peer %s de hash %s" % (peer,clave)
                     #self.printer.msg(self.id,msg_temp)
                     #print "Eliminando a peer",peer,"de hash",clave
    
    def get_peers(self,torrent_hash,type_push):
         
        if not self.torrents.has_key(torrent_hash):
            print "No existe este hash"
            return None
    
        if len(self.torrents[torrent_hash]) < 2:
            num_peers=1
        else:
            num_peers = 2
            
        if type_push == True:
            peers_incompletos = {k: v for k, v in self.torrents[torrent_hash].items() if v['seed'] == False }
            if len(peers_incompletos) == 0: 
                return None
            temp =random.sample(peers_incompletos.keys(),num_peers)
            lista = []
            for peer in temp:
                lista.append(self.torrents[torrent_hash][peer]['ref'])
            return lista
        else:
            temp =random.sample(self.torrents[torrent_hash].keys(),num_peers)
            lista = []
            for peer in temp:
                lista.append(self.torrents[torrent_hash][peer]['ref'])
            return lista
            
    
    def setComplet(self,torrent_hash,peer):
        self.torrents[torrent_hash][peer]['seed']=True

        
class Peer(object):
    _tell = ['announce','setProxys','tracker_announce','announce_stop','setPeers','checkComplet', 'setContent','setInit', 'startPush', 'push', 'makeSeed','startPull', 'pull','pullpush','startPullPush']
    _ask = ['getChunk']
    _ref = ['setProxys']

    def __init__(self):
        self.torrents = {}
 
    def announce(self, torrent_hash, size):
        if not self.torrents.has_key(torrent_hash):
            self.torrents[torrent_hash] = {}
            self.torrents[torrent_hash]['content'] = {}
        self.torrents[torrent_hash]['size'] = size
        self.torrents[torrent_hash]['chunksNeed'] = []
        for i in range(size):
            self.torrents[torrent_hash]['chunksNeed'].append(i)
        self.torrents[torrent_hash]['interval']=interval(self.host, 3, self.proxy, "tracker_announce", torrent_hash)
        
    def setProxys(self,tracker,printer):
        self.tracker = tracker
        self.printer = printer
        
    def tracker_announce(self, torrent_hash):
        self.tracker.announce(torrent_hash,self)
       
    def announce_stop(self, torrent_hash):
        if self.torrents.has_key(torrent_hash):
            self.torrents[torrent_hash]['interval'].set()

    def setContent(self, torrent_hash, chunk_id, chunk_data):
        if not (self.torrents[torrent_hash]['content'].has_key(chunk_id)):
            self.torrents[torrent_hash]['content'][chunk_id] = chunk_data
            #print "-----RECIBIDO ",chunk_data,"-",self.id," Mensaje actual: ",self.torrents[torrent_hash]['content']
            self.printer.update(torrent_hash,self.id,1,self.torrents[torrent_hash]['content'])
            if pull == True:
                self.torrents[torrent_hash]['chunksNeed'].remove(chunk_id)
            if self.checkComplet(torrent_hash):
                #print "El paquete recibido es:",self.id,self.torrents[torrent_hash]['content']
                self.printer.close(torrent_hash,self.id,self.torrents[torrent_hash]['content'])
            
    def startPush(self, torrent_hash):
        self.torrents[torrent_hash]['interval2']=interval(self.host, 1, self.proxy, "push", torrent_hash, None)
        self.printer.create(torrent_hash,self.id,self.torrents[torrent_hash]['size'])

    def startPull(self, torrent_hash):
        self.torrents[torrent_hash]['interval2']=interval(self.host, 1, self.proxy, "pull", torrent_hash, None)
        self.printer.create(torrent_hash,self.id,self.torrents[torrent_hash]['size'])
   
    def startPullPush(self, torrent_hash):
        self.torrents[torrent_hash]['interval2']=interval(self.host, 1, self.proxy, "pullpush", torrent_hash)    
        self.printer.create(torrent_hash,self.id,self.torrents[torrent_hash]['size'])

    def checkComplet(self, torrent_hash): # Nos dice si un torrent_hash ya esta completo
        return (len(self.torrents[torrent_hash]['content'])==self.torrents[torrent_hash]['size']) #TRUE si se tiene el seed completo, FALSE si no lo esta
        
    def push(self, torrent_hash,peers):
        if peers == None:
            try:
                peers = self.tracker.get_peers(torrent_hash,False)
            except TimeoutError:
                None
        #print "PUSH",self.torrents[torrent_hash]['recived'],self.id,torrent_hash
        # Comprobamos si ya tenemos alguna parWte para poderla enviar.
        if len(self.torrents[torrent_hash]['content']) > 0:
            # Cogemos 1 parte al azar (En caso de tener alguna)
            chunk_id = random.sample(self.torrents[torrent_hash]['content'].keys(),1)
            chunk_id = chunk_id[0]
            chunk_data = self.torrents[torrent_hash]['content'][chunk_id]
            #Cogemos 2 peers al azar
            #Enviamos el chunk a todos los peers seleccionados
            if not peers is None:
                for p in peers:
                    if(p != self):
                        try:
                            if (not p.checkComplet(torrent_hash)):
                                p.setContent(torrent_hash, chunk_id, chunk_data)
                        except TimeoutError:
                                None

                        
                        
    def pull(self, torrent_hash,peers):
        if peers == None:
            try:
                peers = self.tracker.get_peers(torrent_hash,False)
            except TimeoutError:
                None
        if not self.checkComplet(torrent_hash):
            #Solictamos a tracker que nos de peer para solicitar ese chunk
            #Les pedimos aquellos chunks que no tenemos (indices en chunksNeed) y si lo tienen, lo eliminamos de la lista de chunksNeed
            if not peers is None:
                for p in peers: 
                    if p != self:
                        try:
                            if len(self.torrents[torrent_hash]['chunksNeed']) > 0:
                                chunk_id = self.torrents[torrent_hash]['chunksNeed'][0]
                                chunk_data = p.getChunk(torrent_hash, chunk_id)
                                if chunk_data != None:
                                    self.setContent(torrent_hash, chunk_id, chunk_data)
                        except TimeoutError:
                            None

    
    def pullpush(self, torrent_hash):
        try:
            peers = self.tracker.get_peers(torrent_hash,False) 
            if not self.checkComplet(torrent_hash):
                self.pull(torrent_hash,peers)
            self.push(torrent_hash,peers)
        except TimeoutError:
                None
        
        
    
    
    def getChunk(self, torrent_hash, chunk_id):
        if (self.torrents[torrent_hash]['content'].has_key(chunk_id)):
            return self.torrents[torrent_hash]['content'][chunk_id]
        return None

    def makeSeed(self, torrent_hash, content):
        for i in range( len(content) ):
            self.torrents[torrent_hash]['content'][i]=content[i]
        self.printer.update(torrent_hash,self.id,self.torrents[torrent_hash]['size'],content)
        self.printer.close(torrent_hash,self.id,content)
        #self.torrents[torrent_hash]['pbar'].update(self.torrents[torrent_hash]['size']-1)
        #self.torrents[torrent_hash]['pbar'].close()
            #self.torrents[torrent_hash]['content'][i].append(content[i])
        


class Printer(object):
    _tell = ['create','close','msg','update']
    torrents = {}
    def msg(self,idmsg,msg):
        #print idmsg,msg
        None
    def create(self,torrent_hash,peer,size):
        if not self.torrents.has_key(torrent_hash):
            self.torrents[torrent_hash] = {}
        if not self.torrents[torrent_hash].has_key(peer):
            self.torrents[torrent_hash][peer] = {}
        frase_temp="%s %s" % (peer,torrent_hash)
        bar_temp="{l_bar}{bar}|{n_fmt}/{total_fmt}-{elapsed}"
        #Para probar PRINT sin parte grafica hay que comentar la siguiente linea, la del update y la dos del close y descomentar los prints que se quiera ver
        #self.torrents[torrent_hash][peer]['pbar'] = tqdm(total=size,desc=frase_temp,bar_format=bar_temp,ncols=100)
    def update(self,torrent_hash,peer,uds,content):
        print "-----RECIBIDO -",peer," Mensaje actual: ",content
        #self.torrents[torrent_hash][peer]['pbar'].update(uds)
    def close(self,torrent_hash,peer,content):
        global contador
        print "FINALIZADO!",peer,"Mensaje:",content
        contador += 1
        #print "han acabado ",self.count
        msg_temp = "%s %s FINALIZADO" % (peer,torrent_hash)
        #self.torrents[torrent_hash][peer]['pbar'].set_description(msg_temp)
        #self.torrents[torrent_hash][peer]['pbar'].close()
        global time_ini
        
        time_act = time.time()
        time_dif = time_act-time_ini
        
        file_temp = "tiempos%speers.txt"  % (total)
        outfile = open(file_temp, 'a')

        c = str(time_dif) + ','
        outfile.write(c)
        outfile.close()


if __name__ == "__main__":
    set_context()
    global contador
    contador = 0
    global time_ini
    global type_exe
    global total
    time_ini = time.time()
    if len(sys.argv) < 3 or not sys.argv[1].isdigit() or not sys.argv[2].isdigit() or int(sys.argv[1]) < 1 or int(sys.argv[1]) > 3:
        print "Falta un parametro o este es incorrecto (Parametros:  [1 Push  2 Pull 3 Pull&Push] [num_peers])"
        print "Ejemplo: ",sys.argv[0]," 1 10"
        print "Ejemplo: ",sys.argv[0]," 2 10"
        print "Ejemplo: ",sys.argv[0]," 3 20"
        shutdown()
    else:
        total = int(sys.argv[2])
        if int(sys.argv[1]) == 1:
            push = True
            pull = False
            print "Version Push con",total,"peers arrancando..."
            type_exe = "1"
            file_temp = "tiempos%speers.txt"  % (total)
            outfile = open(file_temp, 'a')
            for i in range(total+1):
                c = str(i) + ','
                outfile.write(c)
            outfile.close()
            
        elif int(sys.argv[1]) == 2:
            pull = True
            push = False
            print "Version Pull con",total,"peers arrancando..."
            type_exe = "2"
        else:
            push = True
            pull = True
            print "Version Pull&Push con",total,"peers arrancando..."
            type_exe = "3"

            
        
        
        file_temp = "tiempos%speers.txt"  % (total)
        outfile = open(file_temp, 'a')

        c = '\n' + type_exe+ ','
        outfile.write(c)
        outfile.close()
        
        
        h = create_host()
        tracker = h.spawn('tracker', Tracker)
        printer = h.spawn('printer',Printer)
        tracker.setProxys(printer)
        tracker.active_interval()
        
        sleep(1)
        
        torrent_hash1 = "goTorrent"
        mensaje1 = "goTorrent"

        seed = h.spawn('Seed', Peer)
        seed.setProxys(tracker,printer);
        seed.announce(torrent_hash1,len(mensaje1))
        if push == True:
            seed.startPush(torrent_hash1)
            
        seed.makeSeed(torrent_hash1, mensaje1)
        
        peers = {}
        
        for i in range(total):
            peer = "Peer%d" % (i)
            peers[i] = h.spawn(peer, Peer)
            peers[i].setProxys(tracker,printer)
            peers[i].announce(torrent_hash1, len(mensaje1))
            if pull == True and push == False:
                peers[i].startPull(torrent_hash1)
            elif push == True and pull == False:
                peers[i].startPush(torrent_hash1)
            else:
                peers[i].startPullPush(torrent_hash1)
                
        
        while contador < total +1:
            sleep(1)
    
        shutdown()