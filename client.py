import json
import os
import socket
import time

SERVER_ADDRESS: tuple = ("192.168.1.13", 6666)
RESPONSE_SIZE: int = 2 ** 16

def clear_terminal() -> None: os.system('cls' if os.name == 'nt' else 'clear')
def send_request(request: dict) -> dict:

	sockfd = socket.socket()
	sockfd.connect(SERVER_ADDRESS) 
	sockfd.sendall(bytearray(json.dumps(request), 'ascii'))
	response = sockfd.recv(RESPONSE_SIZE)
	load = json.loads(response)
	sockfd.close()

	return load

def is_valid_username(string: str) -> bool:
	allowed = lambda l: ((ord(l) >= ord('A') and ord(l) <= ord('Z')) or
	 (ord(l) >= ord('a') and ord(l) <= ord('z')) or
	 (ord(l) >= ord('0') and ord(l) <= ord('9')) or
	  l == '_' or l == '.')

	return (isinstance(string, str) and 
		len(string) >= 4 and 
		len([i for i in string if not allowed(i)]) == 0)

class App:

	def __init__(self) -> None:
		self.token         = 0
		self.loaded_groups  = 20
		self.current_group = ''
		self.last_message_order = 0

	def entry_page(self) -> None:
		print("-- Welcome To The CMD Chatter --")
		while True:
			inp = '' 
			while inp != '1' and inp != '2':
				inp = input("1: Log-In\n2: Sign-In\n-> ")

			while True:
				username = input("enter username: ")
				if not is_valid_username(username):
					print("invalid username.\nusable characters are a...z, A...Z, 0...9, dot (.) and underscore (_).\nlength must be of length 4 or more")
					continue
				break
			while True: 
				password = input("enter password: ")
				if len(password) < 6:
					print("invalid password, must be of length 6 or more")
					continue
				break

			request = {"action":"", "payload":{"username":username, "password":password}}

			if inp == '1':
				request['action'] = "login_account"
			elif inp == '2':
				request['action'] = "create_account"
			load = send_request(request)

			if load['state'] == "failure":
				print("Request failed\nReason:{0}\n".format(load['reason']))
			else:
				self.token = load['payload']['user_token']
				if inp == '1'  : print("Logged in...!")
				elif inp == '2': print("Signed in...!")
				break

	def groups_page(self) -> None:
		while True:
			request = {"action":"update_state", "payload":{"user_token": self.token, "page":"groups", "last":self.loaded_groups}}
			load = send_request(request)

			print("\n0: load more groups\n1: create a group\n")
			accum_groups = []
			if load['state'] == "failure":
				print("Request failed\nReason:{0}\n".format(load['reason']))
			else:
				for i, group in enumerate(load['payload']['group_chats'], 2):
					accum_groups.append(group[0])
					print("{0}: {1} -> {2}".format(i, group[0], group[1]))

			inp = input("-> ")
			if inp == '0': self.loaded_groups += 20
			elif inp == '1':
				# get the group name
				while True:
					group_name = input("group name: ")
					if len(group_name) < 4:
						print("invalid group name, must be of length 4 or more")
						continue
					break

				request = {"action":"create_group", "payload":{"user_token": self.token, "group_name": group_name}}
				load = send_request(request)
				if load['state'] == 'failure':
					print("Request failed\nReason:{0}\n".format(load['reason']))
				else:
					print("group chat created")

			# inp.isdigit() for checking negatives
			elif inp.isdigit():
				group_chats = load['payload']['group_chats'] 
				if int(inp) - 2 < len(group_chats):
					self.current_group = accum_groups[int(inp) - 2]
					print(f"-- {self.current_group} --")
					return
				else: print("invalid input")
			else: print("invalid input")

	def chat_page(self) -> None:
		print('type * (star) to update\ntype _ (underscore) to leave\n')
		while True:
			request = {"action":"update_state", "payload":
			{"user_token": self.token, "page":"chat", "group_chat": self.current_group, "last":self.last_message_order}}
			load = send_request(request)

			if load['state'] == 'failure':
				print("Request failed\nReason:{0}\n".format(load['reason']))
			else:
				for message in load['payload']['messages']:
					print("{0} -> {1}".format(message['user_name'], message['message_content']))
				self.last_message_order += len(load['payload']['messages'])

			inp = input("-> ")
			if inp == '*':
				continue
			elif inp == '_':
				self.last_message_order = 0
				break
			request = {"action":"send_message", 
			"payload": {"user_token": self.token, "group_chat": self.current_group, "message_content": inp}}
			load = send_request(request)
			if load['state'] == 'failure':
				print("Request failed\nReason:{0}\n".format(load['reason']))

	def run(self) -> None:
		self.entry_page()
		while True:
			self.groups_page()
			self.chat_page()

if __name__ == "__main__":
	App().run() 

#-> TODO: make the interface less clunky