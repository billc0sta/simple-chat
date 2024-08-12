import json
import socket
import socketserver
from uuid import uuid4

REQUEST_SIZE: int = 2 ** 16

class Message:
	def __init__(self, group_name: str, user_name: str, message_content: str) -> None:
		self.group_name:      str = group_name
		self.user_name:       str = user_name
		self.message_content: str = message_content

class User:
	def __init__(self, name: str, salt_pass: int, logged: bool = False) -> None:
		self.name:        str             = name
		self.salt_pass:   int             = salt_pass
		self.messages:    list[Message]   = []
		self.logged: bool                 = logged


class GroupChat:
	def __init__(self, name: str) -> None:
		self.name:    str           = name
		self.chat:    list[Message] = []

group_chats = {}
user_base   = {}
user_tokens = {} 

class RequestHandler(socketserver.BaseRequestHandler):
	def handle(self) -> None:
		self.buffer = str(self.request.recv(REQUEST_SIZE), 'ascii')
		self.invalid_request = False
		self.response = ''

		try: self.load = json.loads(self.buffer)
		except: self.invalid_request = True
		else:
			action = self.load.get('action')

			if action == "update_state":
				self.handle_update_state()

			elif action == "send_message":
				self.handle_send_message()

			elif action == "create_account":
				self.handle_create_account()

			elif action == "login_account":
				self.handle_login_account()

			elif action == "create_group":
				self.handle_create_group()

			else:
				self.invalid_request = True

			if self.invalid_request:
				self.response = json.dumps({"state":"failure", "reason":"invalid request"})

		self.request.sendall(bytearray(self.response, 'ascii'))

	def handle_update_state(self) -> None:
		payload = self.load.get('payload')
		user = user_base.get(user_tokens.get(payload.get('user_token')))
		last = payload.get('last')
		page = payload.get('page')

		if not user: 
			self.response = json.dumps({"state":"failure", "reason":"invalid user token"})
			return
		if not isinstance(last, int) or not page:
			self.invalid_request = True
			return
		

		if page == "chat":
			group_chat = group_chats.get(payload.get('group_chat'))
			if not group_chat:
				self.response = json.dumps({"state":"failure", "reason":"group chat not found"})
				return

			chat_len = len(group_chat.chat)
			dist = (min(last, chat_len), min(last + 20, chat_len))
			resp = {"state":"success", "payload":{"messages":[]}}
			messages = resp["payload"]["messages"]
			for i in range(dist[0], dist[1]):
				curr_msg = group_chat.chat[i]
				d = {"group_chat":curr_msg.group_name,
	 				"user_name": curr_msg.user_name,
	  				"message_content": curr_msg.message_content}

				messages.append(d)
			self.response = json.dumps(resp)

		elif page == "groups":
			if last > 1000:
				self.response = json.dumps({"state":"failure", "reason":"too much group chats to load"})
				return

			groups_len = len(group_chats)
			dest = min(last, groups_len)
			resp = {"state":"success", "payload":{"group_chats":[]}}
			gchs = resp["payload"]["group_chats"]
			for i, group in enumerate(group_chats.values()):
				if i == dest: break
				last_message = group.chat[-1].message_content if (len(group.chat)) > 0 else "..."
				form = [group.name, last_message]
				gchs.append(form)
			self.response = json.dumps(resp)

		else:
			self.invalid_request = True

	def handle_send_message(self) -> None:
		payload = self.load.get('payload')
		user = user_base.get(user_tokens.get(payload.get('user_token')))
		group_chat = group_chats.get(payload.get('group_chat'))
		message_content = payload.get('message_content')

		if not user or not group_chat or not message_content:
			self.response = {"state":"failure", "reason":""}
			if not user: self.response['reason'] = 'invalid user token'
			elif not group_chat: self.response['reason'] = "group chat not found"
			elif not message_content: self.response['reason'] = 'empty message'
			self.response = json.dumps(self.response)

		else:
			msg = Message(group_chat.name, user.name, message_content)
			user.messages.append(msg)
			group_chat.chat.append(msg)
			self.response = json.dumps({"state":"success"})

	def handle_create_account(self) -> None:
		payload  = self.load.get('payload')
		username = payload.get("username")
		password = payload.get("password")

		# validating username and password
		allowed = lambda l: ((ord(l) >= ord('A') and ord(l) <= ord('Z')) or
		 (ord(l) >= ord('a') and ord(l) <= ord('z')) or
		 (ord(l) >= ord('0') and ord(l) <= ord('9')) or
		  l == '_' or l == '.')

		if (not isinstance(username, str) or 
			len(username) < 4 or 
			len([i for i in username if not allowed(i)]) > 0):
			self.response = json.dumps(
				{"state":"failure", 
				"reason":"invalid username"})
			return

		if (not isinstance(password, str) or
			len(password) < 6):
			self.response = json.dumps(
				{"state":"failure", 
				"reason":"invalid password"})
			return

		if user_base.get(username):
			self.response = json.dumps({"state":"failure", 
				"reason":"username already user"})
			return 

		salt                = hash(password)
		user_base[username] = User(username, salt, True)
		token               = int(uuid4())
		user_tokens[token]  = username
		self.response = json.dumps(
			{"state":"success", 
			"payload":{"user_token": token}})

	def handle_login_account(self) -> None:
		payload  = self.load.get('payload')
		username = payload.get("username")
		password = payload.get("password")
		salt     = hash(password)
		user     = user_base.get(username) 
		if user and salt == user.salt_pass:
			token = int(uuid4())
			user_tokens[token] = username
			self.response = json.dumps(
				{"state":"success",
				 "payload":{"user_token": token}})
		else:
			self.response = json.dumps(
				{"state":"failure", 
				"reason":"invalid username or password"})

	def handle_create_group(self) -> None:
		payload  = self.load.get('payload')
		user = user_base.get(user_tokens.get(payload.get('user_token')))
		if not user:
			self.response = json.dumps({"state":"failure", "reason":"invalid user token"})
		else:
			group_name = payload.get('group_name')
			if not isinstance(group_name, str) or len(group_name) < 4:
				self.response = json.dumps({"state":"failure", "reason":"invalid group name"})
			else:
				group_chat = GroupChat(group_name)
				group_chats[group_name] = group_chat
				self.response = json.dumps({"state":"success"})
			
def main() -> None:
	print("Server Started...!")
	HOST, PORT = '192.168.1.13', 6666
	with socketserver.ThreadingTCPServer((HOST, PORT), RequestHandler) as server:
		server.serve_forever()

if __name__ ==  "__main__":
	main()

#-> TODO: do better testing