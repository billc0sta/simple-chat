import tkinter as tk
import json
import socket
import time

SERVER_ADDRESS: tuple = ("192.168.1.13", 6666)
RESPONSE_SIZE: int = 2 ** 16

def send_request(request: dict) -> dict:

	sockfd = socket.socket()
	sockfd.connect(SERVER_ADDRESS) 
	sockfd.sendall(bytearray(json.dumps(request), 'ascii'))
	response = sockfd.recv(RESPONSE_SIZE)
	load = json.loads(response)
	sockfd.close()

	return load

class LoginPage:
	def __init__(self, parent) -> None:
		self.parent = parent;
		self.choice   = ""
		self.username = ""
		self.password = ""

		self.userLabel = tk.Label(master = parent, text = "username")
		self.passLabel = tk.Label(master = parent, text = "password")
		self.userEntry = tk.Entry(master = parent, width = 40)
		self.passEntry = tk.Entry(master = parent, width = 40)
		self.warnLabel = tk.Label(master = parent, text = "")
		self.logButton = tk.Button(master = parent, text = "Log-In", command = lambda: self.submit("LOGIN"), height = 5, width = 20)
		self.signButton = tk.Button(master = parent, text = "Sign-Up", command = lambda: self.submit("SIGNUP"), height = 5, width = 20)

	def run(self) -> None:
		self.userLabel.grid(row = 0, columnspan = 2)
		self.userEntry.grid(row = 1, columnspan = 2)
		self.passLabel.grid(row = 2, columnspan = 2)
		self.passEntry.grid(row = 3, columnspan = 2)
		self.logButton.grid(row = 4, padx = 50)
		self.signButton.grid(row = 4, column = 1, padx = 50, pady = 20 )
		self.warnLabel.grid(row = 5, column = 0, columnspan = 2)

	def quit(self) -> None:
		self.userLabel.destroy()
		self.passLabel.destroy()
		self.logButton.destroy()
		self.signButton.destroy()
		self.userEntry.destroy()
		self.passEntry.destroy()
		self.warnLabel.destroy()

	def submit(self, choice: str) -> None:
		assert(choice == "LOGIN" or choice == "SIGNUP")

		self.parent.user_name = self.userEntry.get().strip()
		password = self.passEntry.get().strip()
		self.userEntry.delete(0, tk.END)
		self.passEntry.delete(0, tk.END)
		self.choice = choice;

		if not self.is_valid_username():
			self.warnLabel['text'] = "invalid username.\nusable characters are a...z, A...Z, 0...9, dot (.) and underscore (_).\nlength must be of length 4 or more"
		elif len(password) < 6:
			self.warnLabel['text'] = "invalid password, must be of length 6 or more"
		else:
			self.warnLabel['text'] = ""

		request = {"action":"", "payload":{"username":self.parent.user_name, "password":password}}

		if self.choice == "LOGIN":
			request['action'] = "login_account"
		elif self.choice == "SIGNUP":
			request['action'] = "create_account"
		load = send_request(request)

		if load['state'] == "failure":
				self.warnLabel['text'] = load['reason']
		else:
			self.parent.user_token = load['payload']['user_token']
			if self.choice == "LOGIN"   : 
				self.warnLabel['text'] = "Logged in...!"
			elif self.choice == "SIGNUP":
			 	self.warnLabel['text'] = "Signed in...!"

			self.quit()
			GroupPage(self.parent).run()

	def is_valid_username(self) -> bool:
		allowed = lambda l: ((ord(l) >= ord('A') and ord(l) <= ord('Z')) or
		 (ord(l) >= ord('a') and ord(l) <= ord('z')) or
		 (ord(l) >= ord('0') and ord(l) <= ord('9')) or
		  l == '_' or l == '.')

		return (isinstance(self.parent.user_name, str) and 
			len(self.parent.user_name) >= 4 and 
			self.parent.user_name[0].isalpha() and 
			len([i for i in self.parent.user_name if not allowed(i)]) == 0)


class GroupPage:
	def __init__(self, parent) -> None:
		self.parent = parent
		self.groups = []
		self.loadable_groups = 20
		self.warnLabel = tk.Label(parent, text = "")
		self.canvas = tk.Canvas(parent, width=500, height=600, background='gray75', scrollregion=(0, 0, 500, 1000))
		self.createButton = tk.Button(parent, text = "create group", command = self.create_group, width = 30)

	def run(self) -> None:
		self.canvas.grid(row = 0, column = 0)
		self.createButton.grid(row = 1, column = 0)
		self.warnLabel.grid(row = 1, column = 1)
		self.update()

	def quit(self) -> None:
		self.canvas.destroy()
		self.createButton.destroy()
		self.warnLabel.destroy()
		for group in self.groups:
			group[0].destroy()
			group[1].destroy()
			group[2].destroy()

	def join(self, group_name: str) -> None:
		self.parent.current_group = group_name
		self.quit()
		ChatPage(group_name).run()

	def update(self) -> None:
		request = {"action":"update_state", "payload":{"user_token": self.parent.user_token, "page":"groups", "last":self.loadable_groups}}
		load = send_request(request)

		if load['state'] == "failure":
			self.warnLabel['text'] = load['reason']
		else:
			for i, group in enumerate(load['payload']['group_chats']):
				if (i < len(self.groups)):
					self.groups[i][2]['text'] = group[1]
				else:
					self.groups.append((
						(tk.Button(self.canvas, text=f"{i+1} ->", font='Helvetica 18 bold', command = lambda: self.join(group[0])), 
						tk.Label(self.canvas, text=group[0], font='Helvetica 18 bold'),
						tk.Label(self.canvas, text=group[1]))
						))
					self.groups[len(self.groups) - 1][0].grid(row = 0, column = i)
					self.groups[len(self.groups) - 1][1].grid(row = 1, column = i)
					self.groups[len(self.groups) - 1][1].grid(row = 2, column = i)

		self.parent.after(3000, self.update)

	def create_group(self) -> None:
		pass

class ChatPage:
	def __int__(self, group_name) -> None:
		self.group = group_name
		self.loaded_messages = 0

	def run(self) -> None:
		pass 

class App(tk.Tk):
	def __init__(self) -> None:
		super().__init__()
		self.geometry("500x700")
		self.title("ToyMessenger")
		self.resizable(False, False)
		self.user_name = ""
		self.current_group = ""
		self.user_token = 0

	def run(self) -> None:
		LoginPage(self).run()
		self.mainloop()


if __name__ == "__main__":
	App().run() 
