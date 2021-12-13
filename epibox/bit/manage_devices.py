# built-in
import time
from datetime import datetime
import json

# third-party
import numpy as np

# local
from epibox.exceptions.exception_manager import error_kill
from epibox.common.connect_device import connect_device


def start_devices(client, devices, fs, mac_channels, header):

    dig_Out = 0
    now = datetime.now()
    sync_param = {'flag_sync' : 0 , 'inittime' : time.time(), 'strtime': time.time(), 'sync_time' : now.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip('0'), 'dig_Out' : dig_Out, 'close_file' : 0, 'mode': 0, 'diff': 1000, 'save_log': 1, 'count_a': 1000, 'sync_append': 0}
    # mode: 0 if not started acquisition yet (or if paused) and 1 otherwise (used to write in drift_log_file)
    
    for i in range(len(devices)):
        sync_param['sync_arr_'+chr(ord('@')+i+1)] = np.zeros(1000, dtype = float)

    # Initialize devices
    for device in devices:

        if header['service'] == 'Bitalino' or header['service'] == 'Mini':
            channels = [int(elem[1])-1 for elem in mac_channels if elem[0]==device.macAddress]
        else:
            channels = [int(elem[1]) for elem in mac_channels if elem[0]==device.macAddress]
            
        device.start(SamplingRate=fs, analogChannels=channels)

    now = datetime.now()
    print('start {}'.format(datetime.now()))
    sync_param['sync_time'] = now.strftime("%Y-%m-%d %H:%M:%S.%f")

    client.publish('rpi', str(['ACQUISITION ON']))                 
    
    return sync_param


def connect_devices(client, devices, opt, already_timed_out, a_file=None, annot_file=None, drift_log_file=None, files_open=True):

    for mac in opt['devices_mac']:

        init_connect_time = time.time()
        print('Searching for Module...' + mac)

        i = 0
        while client.keepAlive:

            i += 1

            if (time.time() - init_connect_time) > 120:
                error_kill(client, devices, 'Failed to reconnect to devices', 'ERROR', a_file, annot_file, drift_log_file, files_open)

            try:
                
                connected = False
                time.sleep(3)
                connected, devices = connect_device(mac, client, devices)

                if connected and mac in [d.macAddress for d in devices]:
                    now = datetime.now()
                    save_time = now.strftime("%H-%M-%S").rstrip('0')
                    client.newAnnot = ['reconnection'], save_time
                    break

                else:
                    if time.time() - init_connect_time > 3*i:
                        timeout_json = json.dumps(['TRYING TO CONNECT', '{}'.format(mac)])
                        client.publish('rpi', timeout_json)
                    raise Exception

            except Exception as e:

                if not already_timed_out and (time.time() - init_connect_time > 3*i):

                    timeout_json = json.dumps(['TIMEOUT', '{}'.format(mac)])
                    client.publish('rpi', timeout_json)

                    already_timed_out = True

                continue

    return devices



def pause_devices(client, devices):

    for device in devices:

        try:
            device.stop()
        except Exception as e:
            print(e)
            continue

    client.publish('rpi', str(['PAUSED']))

    return devices

