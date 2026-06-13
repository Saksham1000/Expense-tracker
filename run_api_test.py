import requests

BASE='http://127.0.0.1:8000'

print('1) Obtain token')
r = requests.post(BASE + '/api/token-auth/', data={'username':'admin','password':'password'})
print(r.status_code, r.text)
if r.status_code != 200:
    raise SystemExit('token failed')

token = r.json().get('token')
headers = {'Authorization': f'Token {token}'}

print('\n2) Create category')
r = requests.post(BASE + '/api/categories/', json={'name':'Dining','monthly_limit':'200.00'}, headers=headers)
print(r.status_code, r.text)
if r.status_code not in (200,201):
    raise SystemExit('category create failed')
cat = r.json()
cat_id = cat.get('id')

print('\n3) Create expense (EUR)')
r = requests.post(BASE + '/api/expenses/', json={'title':'Dinner out','amount':'45.00','currency':'EUR','category':cat_id,'date':'2026-06-09'}, headers=headers)
print(r.status_code, r.text)
if r.status_code not in (200,201):
    raise SystemExit('expense create failed')

print('\n4) Get summary')
r = requests.get(BASE + '/api/expenses/summary/', headers=headers)
print(r.status_code)
print(r.text)
