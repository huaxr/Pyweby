import requests

x = requests.get('https://www.seebug.org').text
print(x)