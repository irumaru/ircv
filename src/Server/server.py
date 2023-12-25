from websocket_server import WebsocketServer

#設定
key = 'Op90n01f'
port = 60100
host = "192.168.100.6"
#初期化
setsion = {
    "console":{
        "alive":0,
        "client":{}
    },
    "ship":{
        "alive":0,
        "client":{}
    }
}

#開始
def new_client(client, server):
    server.send_message(client, 'SERVER: Client link start! id='+str(client['id']))
    print('SERVER: Client link start! id='+str(client['id']))

#終了
def end_client(client, server):
    if(setsion['console']['client']==client):
        setsion['console']['alive']=0
        print('SERVER: Console link down!')
    elif(setsion['ship']['client']==client):
        setsion['ship']['alive']=0
        if(setsion['console']['alive']==1):
            server.send_message(setsion['console']['client'], 'SERVER: Ship link down!')
        print('SERVER: Ship link down!')

#転送
def received(client, server, message):
    #初期アクセス
    if(message=='console key='+key):
        #コンソールセッション開始
        setsion['console']['alive']=1
        setsion['console']['client']=client
        server.send_message(client, 'SERVER: Console setsion start! id='+str(client['id']))
        print('SERVER: Console setsion start! id='+str(client['id']))
    elif(message=='ship key='+key):
        #船セッション開始
        setsion['ship']['alive']=1
        setsion['ship']['client']=client
        server.send_message(client, 'SERVER: Ship setsion start! id='+str(client['id']))
        if(setsion['console']['alive']==1):
            server.send_message(setsion['console']['client'], 'SERVER: Ship setsion start! id='+str(client['id']))
        print('SERVER: Ship setsion start! id='+str(client['id']))
    #通常転送
    else:
        #Console発データ
        if(setsion['console']['client']==client):
            if(setsion['ship']['alive']==1):
                #正常転送
                server.send_message(setsion['ship']['client'], message)
            else:
                #宛先なし
                server.send_message(client, 'SERVER: Cannot transfer ptcket.')
        #Ship発データ
        elif(setsion['ship']['client']==client):
            if(setsion['console']['alive']==1):
                #正常転送
                server.send_message(setsion['console']['client'], message)
        else:
            server.send_message(client, '503')

#Websocket setting
server = WebsocketServer(port, host=host)
server.set_fn_new_client(new_client)#クライアント接続時
server.set_fn_client_left(end_client)#クライアント切断時
server.set_fn_message_received(received)#メッセージ受信時

#Websocket start
server.run_forever()
