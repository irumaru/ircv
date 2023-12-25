#import module
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import subprocess
import pygame.mixer
import json
import time
import pigpio
from gpiozero import MCP3008


#設定_通信
WS_URL='ws://36.52.207.87:60100' #接続サーバー
WS_KEY = 'Op90n01f' #接続Key
WS_RECONNECT_DELAY=5 #再接続発生時の遅延時間
#設定_推進機
THRUSTER_PWM_FREQUENCY=1000 #pwm周波数
THRUSTER_PWM_RANGE=100 #PWM最大レンジ
#設定_舵
RUDDER_PULSE_MIN=975 #右のパルス幅
RUDDER_PULSE_CENTER=1450 #パルス幅の中央値
RUDDER_PULSE_MAX=1925 #左のパルス幅
RUDDER_PULSE_ONEANGLE=11.1111 #1°のパルス幅
#設定_alive
STATUS_LOOP_DELAY=0.5 #Status取得時の遅延時間

#設定_GPIOピン
#推進関連
GPIO_THRUSTER_R=27 #右機関
GPIO_THRUSTER_L=17 #左機関
GPIO_THRUSTER_RPM_R=24 #右回転数
GPIO_THRUSTER_RPM_L=23 #左回転数
GPIO_DIRECTION=22 #前進, 後進
GPIO_RUDDER=18 #舵
#MCP3008関連
GPIO_MCP3008_1_VREF=3.3
GPIO_MCP3008_1_SS=0

gpio=pigpio.pi()

#DB ステータス
status={
    'power':{
        'i':0.0,
        'e':0.0,
        'p':0.0
    },
    'sensor':{
        'woterTem':0.0,
    },
    'thrusterR':{
        'pwmNow':0,
    },
    'thrusterL':{
        'pwmNow':0,
    },
    'rudder':{
        'angleNow':45
    },
    'direction':0
}

#温度センサ温度算出
def device_LM61CIZ(voltage):
    v=float(-30+(voltage-0.3)*100)
    return v

def device_MCP3008(channel, device):
    try:
        v=MCP3008(channel=channel, device=device)
        return v.value*GPIO_MCP3008_1_VREF
        time.sleep(0.05)
    except SPISoftwareFallback:
        time.sleep(0.05)
        return 0

#Status センサーデータ取得(Ship status)
def status_get():
    global status
    #電源, 水冷
    #電圧
    status['power']['e']=device_MCP3008(channel=0, device=GPIO_MCP3008_1_SS)*3+0.2
    #電流
    status['power']['i']=(device_MCP3008(channel=1, device=GPIO_MCP3008_1_SS)*3-2.46)/0.066
    #電力
    status['power']['p']=status['power']['e']*status['power']['i']
    #水温
    status['sensor']['woterTem']=device_LM61CIZ(device_MCP3008(channel=2, device=GPIO_MCP3008_1_SS))
    #右機関回転数
    #status['thrusterR']['rpm']=thrusterGetRPM(GPIO_THRUSTER_RPM_R)
    #左機関回転数
    #status['thrusterL']['rpm']=thrusterGetRPM(GPIO_THRUSTER_RPM_L)

#TS 機関始動
def thruster_start():
    #GPIO初期化(推進機)
    gpio.set_mode(GPIO_THRUSTER_R, pigpio.OUTPUT)
    gpio.set_PWM_frequency(GPIO_THRUSTER_R, THRUSTER_PWM_FREQUENCY)
    gpio.set_PWM_range(GPIO_THRUSTER_R, THRUSTER_PWM_RANGE)
    gpio.set_PWM_dutycycle(GPIO_THRUSTER_R, 0)
    gpio.set_mode(GPIO_THRUSTER_L, pigpio.OUTPUT)
    gpio.set_PWM_frequency(GPIO_THRUSTER_L, THRUSTER_PWM_FREQUENCY)
    gpio.set_PWM_range(GPIO_THRUSTER_L, THRUSTER_PWM_RANGE)
    gpio.set_PWM_dutycycle(GPIO_THRUSTER_L, 0)
    #GPIO初期化(進行方向)
    gpio.set_mode(GPIO_DIRECTION, pigpio.OUTPUT)
    gpio.write(GPIO_DIRECTION, 0)
    #GPIO初期化(センサー)
    gpio.set_mode(GPIO_THRUSTER_RPM_R, pigpio.INPUT)
    gpio.set_mode(GPIO_THRUSTER_RPM_L, pigpio.INPUT)

#TS 右舷速度変更
def thruster_speedR(speed):
    gpio.set_PWM_dutycycle(GPIO_THRUSTER_R, speed)
    #目標値記録
    global status
    status['thrusterR']['pwmNow']=speed

#TS 左舷速度変更
def thruster_speedL(speed):
    gpio.set_PWM_dutycycle(GPIO_THRUSTER_L, speed)
    #目標値記録
    global status
    status['thrusterL']['pwmNow']=speed

#TS 進行方向切替
def thruster_direction(direction):
    if(status['thrusterR']['pwmNow']==0 and status['thrusterR']['pwmNow']==0):
        gpio.write(GPIO_DIRECTION, direction)
    else:
        ws.send('SHIP  : Cannot direction update')
    status['direction']=direction

#RD 舵始動
def rudder_start():
    #GPIO初期化
    gpio.set_mode(GPIO_RUDDER, pigpio.OUTPUT)
    gpio.set_servo_pulsewidth(GPIO_RUDDER, RUDDER_PULSE_CENTER)

#RD 舵センター移動
def rudder_center():
    while True:
        if(status['rudder']['angleNow']==45):
            break
        elif(status['rudder']['angleNow']>45):
            rudder_angle(status['rudder']['angleNow']-1)
        elif(status['rudder']['angleNow']<45):
            rudder_angle(status['rudder']['angleNow']+1)
        time.sleep(0.2)

#RD 舵角度変更
def rudder_angle(angle):
    #パルス計算
    v=int(RUDDER_PULSE_MIN+angle*RUDDER_PULSE_ONEANGLE)
    #パルス幅安全確認
    if(v>RUDDER_PULSE_MAX):
        v=RUDDER_PULSE_MAX
    #操作
    gpio.set_servo_pulsewidth(GPIO_RUDDER, v)
    #目標値記録
    global status
    status['rudder']['angleNow']=angle


#WS 命令受信
def ws_message(ws, message):
    try:
        #サーバーメッセージ受信
        if(message[:6]=='SERVER'):
            print(message)
            return 0
        #偽装パケット
        if(message=='PACKET'):
            ws.send('SHIP  :Active')
            return 0
        #パース
        opl=json.loads(message)
        oplkey=list(opl.keys())
        #機関ダイナミック制御
        if(oplkey[0]=='dynamic'):
            dynamickey=list(opl['dynamic'].keys())
            for key in dynamickey:
                if(key=='speedR'):
                    thruster_speedR(opl['dynamic']['speedR'])
                elif(key=='speedL'):
                    thruster_speedL(opl['dynamic']['speedL'])
        #舵制御
        elif(oplkey[0]=='angle'):
            rudder_angle(opl['angle'])
        #進行方向切替
        elif(oplkey[0]=='direction'):
            thruster_direction(opl['direction'])
        #機関制御モード
        elif(oplkey[0]=='thrustermode'):
            #dynamic
            if(opl['thrustermode']==1):
                thruster_start()
        #システムコマンド
        elif(oplkey[0]=='system'):
            if(opl['system']=='shutdown'):
                rudder_center()
                cmd="shutdown -h now"
                subprocess.call(cmd.split())
            elif(opl['system']=='restart-os'):
                rudder_center()
                cmd="shutdown -r now"
                subprocess.call(cmd.split())
            elif(opl['system']=='restart-app'):
                rudder_center()
                cmd="systemctl restart ircvc"
                subprocess.call(cmd.split())
        #オーディオコマンド
        elif(oplkey[0]=='audio'):
            if(opl['audio']['cmd']=='play'):
                #読み込み・再生
                fdir=opl['audio']['file']
                ws.send('SHIP  : Audio file='+fdir+'.mp3 loop='+opl['audio']['loop'])
                pygame.mixer.init()
                pygame.mixer.music.load('audio/'+fdir+'.mp3')
                pygame.mixer.music.play(1)
                ws.send('SHIP  : Audio play start!')
            elif(opl['audio']['cmd']=='stop'):
                pygame.mixer.music.stop()
                ws.send('SHIP  : Audio Stop')
    except:
        ws.send('SHIP  : Error ws_message(this)')
        pass


#WS 通信エラー
def ws_error(ws, error):
    print('SHIP WS: '+error)
    ws_reconnect()

#WS 切断
def ws_close(ws):
    print("SHIP WS: Link down!")
    ws_reconnect()

#WS 接続(システム起動)
def ws_open(ws):
    ws.send('ship key='+WS_KEY)#Setsion start
    #センサーデータ取得+送信
    def status_loop():
        while True:
            try:
                status_get()
            except:
                ws.send('SHIP  : Error this statusGet()')
                pass
            ws.send('STATUS: '+json.dumps(status))
            time.sleep(STATUS_LOOP_DELAY)
    #サブプロセス起動
    thread.start_new_thread(status_loop, ())

#WS 再接続
def ws_reconnect():
    print('SHIP WS: Reconnect please wait '+str(WS_RECONNECT_DELAY)+' second...')
    time.sleep(WS_RECONNECT_DELAY)
    ws_start()

#WS 開始
def ws_start():
    print('SHIP WS: Link start! url='+WS_URL)
    ws = websocket.WebSocketApp(WS_URL, on_message=ws_message, on_error=ws_error, on_close=ws_close, on_open=ws_open)
    ws.run_forever()

#実行
rudder_start()
thruster_start()
ws_start()