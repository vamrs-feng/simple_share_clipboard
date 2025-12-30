#!/usr/bin/env python3
import http.server
import socketserver
import webbrowser
import os
import json
from datetime import datetime
import threading

# 共享数据
shared_data = {
    'text': '',
    'image': '',
    'files': [],
    'users': 0
}

# 所有连接的客户端
clients = []

# WebSocket处理类
class WebSocketHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # 提供HTML文件
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/ws':
            # 升级到WebSocket连接
            self.upgrade_to_websocket()
        elif self.path == '/data':
            # 提供当前数据的API
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(shared_data).encode())
        else:
            # 尝试提供静态文件
            try:
                self.send_response(200)
                if self.path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif self.path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                with open(self.path[1:], 'rb') as f:
                    self.wfile.write(f.read())
            except:
                self.send_response(404)
                self.end_headers()
    
    def do_POST(self):
        if self.path == '/update':
            # 处理内容更新
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = json.loads(post_data)
            
            # 更新文本内容
            if 'text' in data:
                shared_data['text'] = data['text']
            
            # 更新图片内容
            if 'image' in data:
                shared_data['image'] = data['image']
            
            # 更新文件列表
            if 'files' in data and isinstance(data['files'], list):
                shared_data['files'] = data['files']
            
            # 广播更新给所有客户端
            self.broadcast_update()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode())
    
    def upgrade_to_websocket(self):
        # 简单的WebSocket升级
        if self.headers.get('Upgrade', '').lower() == 'websocket':
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', 'x3JJHMbDL1EzLkh9GBhXDw==')
            self.end_headers()
            
            # 增加用户计数
            shared_data['users'] += 1
            clients.append(self.connection)
            
            print(f"客户端连接，当前用户数: {shared_data['users']}")
            
            # 发送当前内容给新客户端
            self.send_websocket_message(json.dumps({
                'type': 'init',
                'text': shared_data['text'],
                'image': shared_data['image'],
                'files': shared_data['files'],
                'users': shared_data['users']
            }))
            
            # 广播用户数更新
            self.broadcast_user_count()
            
            # 保持连接并处理消息
            try:
                while True:
                    # 简单的WebSocket消息处理
                    data = self.connection.recv(1024)
                    if not data:
                        break
            except:
                pass
            finally:
                # 减少用户计数
                shared_data['users'] -= 1
                clients.remove(self.connection)
                print(f"客户端断开，当前用户数: {shared_data['users']}")
                self.broadcast_user_count()
    
    def send_websocket_message(self, message):
        # 简单的WebSocket消息发送
        try:
            self.connection.send(f"HTTP/1.1 200 OK\r\nContent-Length: {len(message)}\r\n\r\n{message}".encode())
        except:
            pass
    
    def broadcast_update(self):
        # 广播内容更新给所有客户端
        message = json.dumps({
            'type': 'update',
            'text': shared_data['text'],
            'image': shared_data['image'],
            'files': shared_data['files']
        })
        for client in clients:
            try:
                client.send(f"HTTP/1.1 200 OK\r\nContent-Length: {len(message)}\r\n\r\n{message}".encode())
            except:
                pass
    
    def broadcast_user_count(self):
        # 广播用户数更新
        message = json.dumps({
            'type': 'users',
            'users': shared_data['users']
        })
        for client in clients:
            try:
                client.send(f"HTTP/1.1 200 OK\r\nContent-Length: {len(message)}\r\n\r\n{message}".encode())
            except:
                pass

# 启动服务器
def start_server():
    port = 8000
    handler = WebSocketHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    print(f"服务器启动在 http://localhost:{port}")
    print(f"在局域网中访问 http://<您的IP地址>:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("服务器停止")
        httpd.server_close()

if __name__ == "__main__":
    start_server()

