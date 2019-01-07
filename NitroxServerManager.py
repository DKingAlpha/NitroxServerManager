import os
import sys
import time
import threading
import pickle
import socket
import web


# work in script dir
os.chdir(sys.path[0])

urls = (
    '/server', 'server', 
    '/notify/(.+)/(.+)/(.+)', 'notify'
)


class server:
    def GET(self):
        auth_serverinfo, uniq_server_dict, keepalive = load_data()
        html = ''
        for k in auth_serverinfo:
            html = html + auth_serverinfo[k] + '\r\n'
        return html


def save_data(*args):
    with open('serverdata.pickle', 'wb+') as f:
        pickle.dump(args, f)

def load_data():
    if not os.path.exists('serverdata.pickle'):
        save_data({}, {}, {})
    with open('serverdata.pickle', 'rb') as f:
        return pickle.load(f)


class notify:
    def GET(self, op, pingerid, serverinfo):
        # workaround for not working global here
        auth_serverinfo, uniq_server_dict, keepalive = load_data()

        i_serverstr = serverinfo.rsplit('|', 1)[0]
        i_serveraddr = i_serverstr.rsplit(':', 1)[1]
        i_playernum = serverinfo.rsplit('|', 1)[1]
        if op == 'online':
            if pingerid in auth_serverinfo:
                o_serverstr = auth_serverinfo[pingerid].rsplit('|', 1)[0]
                o_playernum = auth_serverinfo[pingerid].rsplit('|', 1)[1]
                if i_serverstr == o_serverstr:
                    auth_serverinfo[pingerid] = serverinfo
                    uniq_server_dict[i_serveraddr] = pingerid
                    keepalive[pingerid] = time.time()
                    save_data(auth_serverinfo, uniq_server_dict, keepalive)
                    return "Server info updated"
                else:
                    return "Server info rejected"
            else:
                if i_serveraddr in uniq_server_dict:
                    return "Wrong key to update server info! If this is your server, it will recover in next update"
                else:
                    if len(pingerid) == 32:
                        auth_serverinfo[pingerid] = serverinfo
                        uniq_server_dict[i_serveraddr] = pingerid
                        keepalive[pingerid] = time.time()
                        save_data(auth_serverinfo, uniq_server_dict, keepalive)
                        return "Server info registered"
                    else:
                        return "Key too short"
        if op == 'offline':
            if pingerid in auth_serverinfo:
                auth_serverinfo.pop(pingerid)
                uniq_server_dict.pop(i_serveraddr)
                keepalive.pop(pingerid)
                save_data(auth_serverinfo, uniq_server_dict, keepalive)
                return "Server info removed"
            else:
                return "Unknown server"
        return "Unknown Operation"


def clean_outdated_server():
    while True:
        time.sleep(10)
        auth_serverinfo, uniq_server_dict, keepalive = load_data()
        current_time = time.time()
        for id in list(keepalive.keys()):
            delta = current_time - keepalive[id]
            if delta > 12*60: # 12min not updated
                serverinfo = auth_serverinfo.pop(id)
                uniq_server_dict.pop(serverinfo.rsplit('|', 1)[0])
                keepalive.pop(id)
                print(serverinfo + " has not updated since 10 minutes ago. Removing it.")
        save_data(auth_serverinfo, uniq_server_dict, keepalive)


class MyApplication(web.application):
    def run(self, port=80, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))

if __name__ == "__main__":
    app = MyApplication(urls, globals())
    th = threading.Thread(target=clean_outdated_server)
    th.daemon = True
    th.start()
    app.run(port=80)
