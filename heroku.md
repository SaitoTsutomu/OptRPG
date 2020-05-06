## 前提

Herokuのアカウントを作成しておくこと

https://signup.heroku.com/

## 手順
```
git clone https://github.com/SaitoTsutomu/OptRPG.git
cd OptRPG
heroku login  # ブラウザでログインすること
heroku create --buildpack heroku/python
heroku addons:create heroku-postgresql:hobby-dev
git push heroku master
heroku logs
heroku run python -c "from optrpg import init; init()"
heroku open
```

## 終了

```
heroku ps:scale web=0
```
