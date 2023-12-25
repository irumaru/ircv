var config={
    ws: {
        url: 'ws://36.52.207.87:60100',
        key: 'Op90n01f',
        link: 0
    },
    thruster: {
        maxspeed: 100,
        minspeed: 0,
        update: 1
    },
    thruster_static: {
        maxspeed: 9,
        minspeed: 0,
        level: [0, 10, 15, 20, 25, 30, 40, 50, 60, 100],
        levelName: ['停止', '微速', '半速', '源速', '強速', '第一戦速', '第二戦速', '第三戦速', '最大戦速', '一杯']
    },
    thruster_mode: 0,//1でdynamicモード
    rudder: {
        maxangle: 80,
        minangle: 10,
        update: 1
    },
    key:1
}

var opl={
    direction: 0,
    dynamic: {
        speedR: 0,
        speedL: 0
    },
    static: {
        speed: 0
    },
    angle: 45,
    audio:{}
}

//ログ処理
function onlog(log){
    console.log(log);
}

//TH 推進機
function thruster(code){
    if(code==0){//加速
        if(opl.dynamic.speedR<config.thruster.maxspeed){
            opl.dynamic.speedR+=config.thruster.update;
        }
        if(opl.dynamic.speedL<config.thruster.maxspeed){
            opl.dynamic.speedL+=config.thruster.update;
        }
    }else if(code==1){//減速
        if(opl.dynamic.speedR>config.thruster.minspeed){
            opl.dynamic.speedR-=config.thruster.update;
        }
        if(opl.dynamic.speedL>config.thruster.minspeed){
            opl.dynamic.speedL-=config.thruster.update;
        }
    }else if(code==2){//右舷加速
        if(opl.dynamic.speedR<config.thruster.maxspeed){
            opl.dynamic.speedR+=config.thruster.update;
        }
    }else if(code==3){//左舷加速
        if(opl.dynamic.speedL<config.thruster.maxspeed){
            opl.dynamic.speedL+=config.thruster.update;
        }
    }else if(code==4){//右舷減速
        if(opl.dynamic.speedR>config.thruster.minspeed){
            opl.dynamic.speedR-=config.thruster.update;
        }
    }else if(code==5){//左舷減速
        if(opl.dynamic.speedL>config.thruster.minspeed){
            opl.dynamic.speedL-=config.thruster.update;
        }
    }
    //送信
    send({dynamic: opl.dynamic});
    //表示更新
    document.getElementById('statusThrusterRPWMGoal').innerText=opl.dynamic.speedR+'%';
    document.getElementById('statusThrusterLPWMGoal').innerText=opl.dynamic.speedL+'%';
}
//static速度制御
function thruster_static(code){
    if(code==0){
        //加速
        if(config.thruster_static.maxspeed>opl.static.speed){
            opl.static.speed++;
        }
    }else if(code==1){
        //減速
        if(config.thruster_static.minspeed<opl.static.speed){
            opl.static.speed--;
        }
    }
    //画面更新
    document.getElementById('statusThrusterGoal').innerText=config.thruster_static.levelName[opl.static.speed];
}
//static速度制御(操作)
function thruster_static_loop(){
    //途中終了
    if(config.thruster_mode==1){
        return;
    }
    //比較更新
    if(opl.dynamic.speedR<config.thruster_static.level[opl.static.speed]){
        //加速
        thruster(2);
    }else if(opl.dynamic.speedR>config.thruster_static.level[opl.static.speed]){
        //加速
        thruster(4);
    }
    if(opl.dynamic.speedL<config.thruster_static.level[opl.static.speed]){
        //加速
        thruster(3);
    }else if(opl.dynamic.speedL>config.thruster_static.level[opl.static.speed]){
        //加速
        thruster(5);
    }
    //loop
    setTimeout(thruster_static_loop, 500);
}
//出力モード変更
function thruster_modechange(){
    //モードチェンジ
    if(config.thruster_mode==0){
        config.thruster_mode=1;
        document.getElementById('thrusterMode').innerText='Dynamic';
    }else{
        config.thruster_mode=0;
        thruster_static_loop();
        document.getElementById('thrusterMode').innerText='Static';
    }
}
//TH 出力反転
function direction(){
    if(opl.dynamic.speedR==0 && opl.dynamic.speedL==0){
        if(opl.direction==1){
            opl.direction=0;
            document.getElementById('direction').innerText='前進';
        }else{
            opl.direction=1;
            document.getElementById('direction').innerText='後進';
        }
        //送信
        send({direction: opl.direction});
    }
}

//RD 舵
function rudder(code){
    if(code==0){//面舵
        if(opl.angle<config.rudder.maxangle){
            opl.angle+=config.rudder.update;
        }
    }else if(code==1){//取り舵
        if(opl.angle>config.rudder.minangle){
            opl.angle-=config.rudder.update;
        }
    }
    //送信
    send({angle: opl.angle});
    //表示更新
    document.getElementById('statusRudderAngleGoal').innerText=opl.angle-45+'°';
}
//RD 舵センター
function rudder_center(){
    function loop(){
        if(opl.angle==45){
            return;
        }else if(opl.angle>45){
            rudder(1);
            setTimeout(loop, 60);
        }else if(opl.angle<45){
            rudder(0);
            setTimeout(loop, 60);
        }
    }
    loop();
}

//キーイベント
document.addEventListener('keydown', (objectEvent) => {
    if(config.key==0){
        if(objectEvent.keyCode=='13'){
            //コマンド実行
            inputCmd();
        }
        return
    }
    var event=objectEvent.key;
    if(config.thruster_mode==0){
        //Static操船
        if(event=='8' || event=='w'){
            //加速
            thruster_static(0);
        }else if(event=='5' || event=='s'){
            //減速
            thruster_static(1);
        }
    }else{
        //Dynamic操船
        if(event=='8' || event=='w'){
            //加速 code=0
            thruster(0);
        }else if(event=='5' || event=='s'){
            //減速 code=1
            thruster(1);
        }else if(event=='9' || event=='e'){
            //右舷加速 code=2
            thruster(2);
        }else if(event=='7' || event=='q'){
            //左舷加速 code=3
            thruster(3);
        }else if(event=='3' || event=='c'){
            //右舷減速 code=4
            thruster(4);
        }else if(event=='1' || event=='z'){
            //左舷減速 code=5
            thruster(5);
        }
    }
    //舵
    if(event=='4' || event=='a'){
        //取り舵 code=1
        rudder(1);
    }else if(event=='6' || event=='d'){
        //面舵 code=0
        rudder(0);
    }else if(event=='2' || event=='x'){
        //出力反転
        rudder_center();
    }
});
//コマンド
function inputCmd(){
    var cmd=document.getElementById("inputCmd").value;
    cmd=cmd.split(' ');
    if(cmd[0]=='system'){
        //システムコマンド
        opl.system=cmd[1];
        send({system: opl.system});
    }else if(cmd[0]=='audio'){
        //オーディオコマンド
        if(cmd[1]=='play'){
            opl.audio.cmd=cmd[1];
            opl.audio.file=cmd[2];
            opl.audio.loop=cmd[3];
        }else if(cmd[1]=='stop'){
            opl.audio.cmd=cmd[1];
        }
        send({audio: opl.audio});
    }
}
//入力変更
function inputChange(){
    if(config.key==1){
        config.key=0;
        document.getElementById('inputMode').innerText='コマンドモード';
    }else{
        config.key=1;
        document.getElementById('inputMode').innerText='WASDモード';
    }
}

//WS 宣言
var ws=new WebSocket(config.ws.url);

//送信
function send(data){
    if(config.ws.link==1){
        ws.send(JSON.stringify(data));
        console.log(JSON.stringify(data));
    }else{
        console.log('Cannot send packet: '+JSON.stringify(data));
    }
}

//WS 接続開始
ws.onopen = function() {
    ws.send('console key='+config.ws.key);
    nullPacket();
    config.ws.link=1;
};

//WS エラー発生
ws.onerror = function(error) {
    onlog('CONSOLE WS: Error '+error);
    config.ws.link=0;
};

//WS 通信切断
ws.onclose = function() {
    onlog('CONSOLE WS: Link Down!');
    config.ws.link=0;
};

//WS メッセージ受信
ws.onmessage = function(message) {
    if(message.data.slice(0,6)=='SERVER'){
        onlog(message.data);
    }
    if(message.data.slice(0,6)=='SHIP  '){
        onlog(message.data);
    }
    if(message.data.slice(0,6)=='STATUS'){
        message=message.data.slice(8);
        //パース
        var status=JSON.parse(message);
        //電源
        var capacity=(status.power.e-7.4)*100;
        //fixed
        document.getElementById('statusPowerI').innerText=status.power.i;
        document.getElementById('statusPowerV').innerText=status.power.e;
        document.getElementById('sensorPowerCapacity').innerText=capacity;
        //水冷
        document.getElementById('statusSensorWoterRem').innerText=status.sensor.woterTem;
        //右舷
        document.getElementById('statusThrusterRPWMNow').innerText=status.thrusterR.pwmNow+'%';
        //左舷
        document.getElementById('statusThrusterLPWMNow').innerText=status.thrusterL.pwmNow+'%';
        //舵
        document.getElementById('statusRudderAngleNow').innerText=status.rudder.angleNow-45+'°';
    }
};

//空パケット
function nullPacket(){
    ws.send('PACKET');
    setTimeout(nullPacket, 5000);
}

//初期実行
thruster_static_loop();