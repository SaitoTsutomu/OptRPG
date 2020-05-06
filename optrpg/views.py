import re
from datetime import datetime
from itertools import groupby
from pathlib import Path
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile

import pandas as pd
import toml
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from more_itertools import ilen, repeat_last

version = "0.0.1"

app = Flask(__name__)
app.config.from_object("optrpg.config")
db = SQLAlchemy(app)

pwd = Path(__file__).parent
data = toml.load(str(pwd / "data.toml"))


class Bingo(db.Model):
    __tablename__ = "bingo"

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Text)
    prob = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<id={self.user} title={self.prob}>"


def init():
    """
    poetry run python -c "from optrpg import init; init()"
    """
    db.create_all()


def main():
    app.run(app.config.get("HOST"), app.config.get("PORT"), use_reloader=True)


@app.route("/")
def index():
    return render_template("index.html", version=version)


def get_bingo(user, prob):
    return db.session.query(Bingo).filter(Bingo.user == user, Bingo.prob == prob)


def execpy(src):
    with NamedTemporaryFile(mode="w", encoding="utf8", suffix=".py") as fp:
        fp.write(src)
        fp.flush()
        pr = Popen(["python", fp.name], stdout=PIPE, stderr=PIPE, cwd=str(pwd))
        pr.wait()
        for st in (pr.stderr, pr.stdout):
            s = st.read().decode().strip()
            if s:
                break
    return s


def sani(s):
    return re.sub(r"(import|eval|exec)", " ", s)


@app.route("/quest/<prob>", methods=["GET", "POST"])
def quest(prob):
    prdt = data["probs"][prob]
    src = prdt["answer"].rstrip() if "ok" in request.args else prdt["src"].rstrip()
    pages = list(data["probs"].keys())
    page = pages.index(prob)
    message, ok = "", False
    if request.method == "POST":
        user = session["user"] = request.form["user"]
        src = request.form["src"]
        s = execpy(f"{prdt['header'].rstrip()}\n{sani(src)}\n{prdt['footer'].rstrip()}")
        ok = s == prdt["result"]
        if ok:
            get_bingo(user, prob).delete()
            created_at = datetime.now().replace(microsecond=0)
            db.session.add(Bingo(user=user, prob=prob, created_at=created_at))
            db.session.commit()
            nxt = "/finish" if page == len(pages) - 1 else f"/quest/{pages[page + 1]}"
            message = f'正解です! &nbsp; <a href="{nxt}">次へ進む</a><hr>'
        else:
            message = (
                f'結果<br><pre class="result">{s}</pre><br>判定：違います'
                f'<p><a href="/answer/{prob}" target="_blank">解答を見る</a></p>'
            )
    return render_template(
        "problem.html",
        version=version,
        title=f"{page + 1}階ボス - " + prdt["title"],
        message=message,
        prob=prob,
        prdt=prdt,
        user=session.get("user", ""),
        src=src,
    )


@app.route("/answer/<prob>")
def answer(prob):
    prdt = data["probs"][prob]
    return render_template("answer.html", version=version, prob=prob, prdt=prdt)


@app.route("/finish")
def finish():
    message = f'{session.get("user", "名無し")} さん、おめでとう'
    return render_template("finish.html", version=version, message=message)


@app.route("/users")
def users():
    bingos = Bingo.query.all()
    n = len(data["probs"])
    group = [
        (user, 100 * ilen(gr) // n)
        for user, gr in groupby(bingos, key=lambda bng: bng.user)
    ]
    return render_template("users.html", version=version, group=group)


@app.route("/logs")
def logs():
    bingos = Bingo.query.all()
    return render_template("logs.html", version=version, bingos=bingos)


@app.route("/clear/<user>")
def clear(user):
    if user == "all":
        db.session.query(Bingo).delete()
    else:
        db.session.query(Bingo).filter(Bingo.user == user).delete()
    db.session.commit()
    return redirect(url_for("users"))


@app.route("/table/<file>")
def table(file):
    df = pd.read_csv(pwd / "csv" / file)
    return render_template(
        "table.html",
        version=version,
        file=file,
        df=df,
        getattr=getattr,
        zip=zip,
        repeat_last=repeat_last,
    )


@app.route("/csv/<file>")
def csv(file):
    return send_file(
        str(pwd / "csv" / file),
        as_attachment=True,
        attachment_filename=file,
        mimetype="text/csv",
    )
