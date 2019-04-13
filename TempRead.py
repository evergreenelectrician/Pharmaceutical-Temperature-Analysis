#email_conf is a custom library made to save private credentials :P 
import json, email_conf, time, math, statistics
from boltiot import Email, Bolt
from datetime import datetime

FRAME_SIZE = 3
MUL_FACTOR = 5

min_permlimit = -40    #minumum permanent limit
max_permlimit = -30    #maximum permanent limit

min_templimit = -33  #minimum temporary limit
max_templimit = -30  #maximum temporary limit
temptimelimit = 1200 #time limit (in seconds) at which the range could be at. 

def compute_bounds(history_data,frame_size,factor):  #Z-Score analysis bound function
    if len(history_data)<frame_size :
        return None

    if len(history_data)>frame_size :
        del history_data[0:len(history_data)-frame_size]
    Mn=statistics.mean(history_data)
    Variance=0
    for data in history_data :
        Variance += math.pow((data-Mn),2)
    Zn = factor * math.sqrt(Variance / frame_size)
    High_bound = history_data[frame_size-1]+Zn
    Low_Bound = history_data[frame_size-1]-Zn
    return [High_bound,Low_Bound]

def buzz(t):                                         #buzz function
    r = mybolt.digitalWrite('0', 'HIGH')
    time.sleep(t)
    r = mybolt.digitalWrite('0', 'LOW')

file=open("Templog.txt","a")    #file inserted with an empty new line everytime the code is initially run 
file.write('\n')
file.close()
mybolt = Bolt(email_conf.API_KEY, email_conf.DEVICE_ID)
mailer = Email(email_conf.MAILGUN_API_KEY,email_conf.SANDBOX_URL, email_conf.SENDER_EMAIL, email_conf.RECIPIENT_EMAIL)
history_data=[]
time_count=0
flag=0
while True:                               #loop begins
    response = mybolt.analogRead('A0')
    data = json.loads(response)
    if data['success'] != '1':
        print("Data Error,",end=' ')
        print(data['value'])
        time.sleep(10)
        continue
    sensor_value=0
    try:                                  #reading, printing and writing data to file
        sensor_value = int(data['value'])
        Temperature=(100*sensor_value)/1024       
        b=datetime.now() 
        file=open("Templog.txt","a")
        a=str("%.3f"%Temperature)+" at "+str("%02d"%b.hour)+":"+str("%02d"%b.minute)+":"+ str("%02d"%b.second)
        print(a)
        a=a+"  "+str("%02d"%b.day)+"/"+str("%02d"%b.month)+"/"+ str("%02d"%b.year)
        file.write(a)
        file.write('\n')
        file.close()

    except Exception as e:
        print("Response Error",e)
        continue

    bound = compute_bounds(history_data,FRAME_SIZE,MUL_FACTOR)
    if not bound:
        required_data_count=FRAME_SIZE-len(history_data)
        print("Computing Z-score. Remaining:", required_data_count)
        print()
        history_data.append(Temperature)
        time.sleep(10)
        continue
    try:                            #cautions and warning checks
        c=b.hour*3600+b.minute*60+b.second

        #To check the temporary range limits
        if Temperature>=min_templimit and Temperature<=max_templimit:
            if flag==0:
                a=b.hour*3600+b.minute*60+b.second
                time_count=a+temptimelimit
                flag=1 
            elif c>=time_count:
                print ("WARNING, Temperature at critical range")
                buzz(0.1)
                response = mailer.send_email("WARNING: Critical Range", "The Temperature has been between "+str(min_templimit)+" and "+str(max_templimit)+"for the last "+str(temptimelimit/60)+" minute(s). Current Temperature is:" +str(Temperature))       
                flag=0
                time_count=0 
        else:
            time_count=0    
            flag=0
        
        #To check permament limits
        if Temperature > max_permlimit :
            print ("WARNING, Temperature is above permanent range")
            buzz(0.5)
            response = mailer.send_email("WARNING: Limit Crossed", "Temperature above permanent range, Current Temperature is:" +str(Temperature))
        
        elif Temperature < min_permlimit:
            print ("WARNING, Temperature is below permanent limit")
            buzz(0.5)
            response = mailer.send_email("WARNING: Limit Crossed", "Temperature below permanent range, Current Temperature is:" +str(Temperature))
        

        #To checks for anomaly
        if Temperature > bound[0] :
            print ("CAUTION, Anomaly rise detected")
            buzz(0.05)
            response = mailer.send_email("CAUTION: Door was Opened", "Anomaly rise detected, Current Temperature is:" +str(Temperature))
        
        elif Temperature < bound[1]:
            print ("CAUTION, Anomaly fall detected")
            buzz(0.05)
            response = mailer.send_email("CAUTION: Door was Opened", "Anomaly fall detected, Current Temperature is:" +str(Temperature))
        
        
        history_data.append(Temperature)

    except Exception as e:
        print ("Error",e)
    print()
    time.sleep(10)