# coding=utf-8
from flask import Flask, make_response, render_template, flash, redirect, session, url_for, request, g, Markup
from app import app, db, log
import redis
import logging
from const import *
import bcrypt
import threading
import time
import random
import string
import os
import re
import json
import uuid


@app.before_first_request
def setup():
    log.setLevel(logging.DEBUG)
    sessions = db.hkeys("sessions_app")
    for session in sessions:
        db.hdel("sessions_app", session)


@app.route('/', methods=[GET])
def home():
    return render_template('home.html'), 200


@app.route('/login', methods=[POST, GET])
def login():
    if request.method == POST:
        form = request.form
        username = form["username"]
        password = form.get("password").encode("utf-8")
        res = db.hexists(username, "data")
        if res == 0:
            return render_template("login.html"), 404
        salt = db.hget(username, "passwd_salt").encode("utf-8")
        for i in range(10):
            hashed_passwd = bcrypt.hashpw(password,salt)
            password = hashed_passwd
        password = str(hashed_passwd)
        cor_password = db.hget(username, "passwd_hash")
        if password == cor_password:
            response = make_response(redirect(url_for('home')))
            sessionid = uuid.uuid4().hex
            response.set_cookie("app_session", sessionid,secure=True, httponly=True, samesite="Strict")
            db.hset("sessions_app", sessionid, username)
            log.debug("session is set ")
            threading.Thread(target=removeUserSession,args=(sessionid, 600,)).start()
            time.sleep(0.2)
            return response, 200
        else:
            return render_template("login.html"), 403
    else:
        return render_template("login.html"), 200


@app.route('/notes', methods=[GET, POST])
def notes():
    sessionid = request.cookies.get("app_session")
    log.debug(sessionid)
    if sessionid == None:
        log.debug("session id is lost")
        return redirect(url_for('login'))
    current_user = db.hget("sessions_app", sessionid)
    if current_user == None:
        log.debug("session id is bad")
        return redirect(url_for('login'))
    if request.method == POST:
        form = request.form
        noteid = uuid.uuid4().hex
        title = form.get("title")
        text = form.get("text")
        usersff = form.get("users")
        users = []
        if usersff != "" and usersff != None:
            usersff = usersff.split(";")
            for user in usersff:
                user = user.replace(" ","")
                res = db.hexists(user, "data")
                if res == 0:
                    return {'msg': "Uzytkownik %s nie istnieje" % user}
            for user in usersff:
                user = user.replace(" ","")
                users.append(user)
                notesforhim = db.hget(user,"notesforme")
                notesforhim = json.loads(notesforhim)
                notesforhim['notes'].append(noteid)
                db.hset(user,"notesforme", json.dumps(notesforhim))
        public = form["public"]
        if public == "True":
            public = "True"
        else:
            public = "False"
        #create new note (TITLE, TEXT OWNER, PUBLIC, USERS)
        db.hset(noteid,"title",title)

        db.hset(noteid,"text",text)

        db.hset(noteid,"owner",current_user)

        db.hset(noteid,"public", public)

        db.hset(noteid,"users",json.dumps({'users':users}))

        if public == "True":
            db.hset("public::notes",noteid,"True")
        yournotes = db.hget(current_user,"notes")
        yournotes = json.loads(yournotes)
        yournotes["notes"].append(noteid)
        db.hset(current_user,"notes",json.dumps(yournotes))
        notes =[]
        if len(yournotes["notes"]) > 0:
            for note in yournotes["notes"]:
                note = {
                    'id': note,
                    'title': db.hget(note, "title"),
                    'text' : db.hget(note, "text")
                }
                notes.append(note)
        public_notes = []
        publicnotesid = db.hkeys("public::notes")
        for nid in publicnotesid:
            note = {
                    'id': nid,
                    'title': db.hget(nid, "title"),
                    'text' : db.hget(nid, "text")
                }
            public_notes.append(note)
        notes_for_me = []
        notesforme = db.hget(current_user,"notesforme")
        notesforme = json.loads(notesforme)
        for nid in notesforme['notes']:
            note = {
                    'id': nid,
                    'title': db.hget(nid, "title"),
                    'text' : db.hget(nid, "text")
                }
            notes_for_me.append(note)
        return render_template("notes.html", notes = notes, public_notes=public_notes, notes_for_me = notes_for_me)
    else:    
        yournotes = db.hget(current_user,"notes")
        yournotes = json.loads(yournotes)
        notes =[]
        if len(yournotes["notes"]) > 0:
            for note in yournotes["notes"]:
                note = {
                    'id': note,
                    'title': db.hget(note, "title"),
                    'text' : db.hget(note, "text")
                }
                notes.append(note)
        public_notes = []
        publicnotesid = db.hkeys("public::notes")
        for nid in publicnotesid:
            note = {
                    'id': nid,
                    'title': db.hget(nid, "title"),
                    'text' : db.hget(nid, "text")
                }
            public_notes.append(note)
        notes_for_me = []
        notesforme = db.hget(current_user,"notesforme")
        notesforme = json.loads(notesforme)
        for nid in notesforme['notes']:
            note = {
                    'id': nid,
                    'title': db.hget(nid, "title"),
                    'text' : db.hget(nid, "text")
                }
            notes_for_me.append(note)
        return render_template("notes.html", notes = notes, public_notes=public_notes,notes_for_me=notes_for_me)


@app.route('/registration', methods=[POST, GET])
def registration():
    if request.method == GET:
        return render_template("registration.html")
    else:
        form = request.form
        # data validation
        isValid, msg = validate_userform(form)
        if not isValid:
            return {'msg': msg}, 400
        isValid, msg = validate_password(form)
        if not isValid:
            return {'msg': msg}, 400
        isValid, msg = validate_question(form)
        if not isValid:
            return {'msg': msg}, 400
        # user data save
        user = to_user(form)
        notes = json.dumps({'notes': []})
        user_data = json.dumps(user.user_to_dict())
        db.hset(user.login, "data", user_data)
        db.hset(user.login, "notes", notes)
        db.hset(user.login, "notesforme", notes)
        # password hash & save
        password = form.get("password").encode("utf-8")
        salt = bcrypt.gensalt(12)
        for i in range(10):
            hashed_passwd = bcrypt.hashpw(password,salt)
            password = hashed_passwd
        salt = str(salt)
        password = str(hashed_passwd)
        db.hset(user.login, "passwd_hash", password)
        db.hset(user.login, "passwd_salt", salt)
        # answer hash & save
        question = form.get("question")
        answer = form.get("answer").encode("utf-8")
        salt = bcrypt.gensalt(12)
        for i in range(10):
            hashed_answer = bcrypt.hashpw(answer,salt)
            answer = hashed_answer
        salt = str(salt)
        answer = str(hashed_answer)
        db.hset(user.login, "question", question)
        db.hset(user.login, "answer_hash", answer)
        db.hset(user.login, "answer_salt", salt)
        return redirect(url_for('home')), 200


@app.route('/myprofile', methods=[GET,POST])
def profile():
    sessionid = request.cookies.get("app_session")
    log.debug(sessionid)
    if sessionid == None:
        log.debug("session id is lost")
        return redirect(url_for('login'))
    current_user = db.hget("sessions_app", sessionid)
    if current_user == None:
        log.debug("session id is bad")
        return redirect(url_for('login'))
    edit = 'hidden'
    if request.method == POST:
        edit = ''
    user_data = db.hget(current_user, "data")
    user_data = json.loads(user_data)
    return render_template('myprofile.html', user=user_data, edit = edit), 200
    
@app.route('/changeprofile', methods=[POST])
def changeprofile():
    sessionid = request.cookies.get("app_session")
    log.debug(sessionid)
    if sessionid == None:
        log.debug("session id is lost")
        return redirect(url_for('login'))
    current_user = db.hget("sessions_app", sessionid)
    if current_user == None:
        log.debug("session id is bad")
        return redirect(url_for('login'))
    form = request.form
    isValid, msg = validate_updateuserform(form)
    if not isValid:
        return {'msg': msg}, 400
    
    fname = form.get("firstName")
    lname = form.get("lastName")
    phone = form.get("phone")
    street = form.get("street")
    number = form.get("streetNumber")
    postalCode = form.get("postalCode")
    city = form.get("city")
    country = form.get("country")

    user_data = db.hget(current_user, "data")
    user_data = json.loads(user_data)

    user_data['fname'] = fname
    user_data['lname'] = lname
    user_data['phone'] = phone
    user_data['address']['street'] = street
    user_data['address']['number'] = number
    user_data['address']['postalCode'] = postalCode
    user_data['address']['city'] = city
    user_data['address']['country'] = country

    db.hset(current_user, "data", json.dumps(user_data))

    return redirect(url_for("profile")),200


@app.route("/logout", methods=[GET])
def logout():
    resp = make_response(render_template("login.html"))
    sessionid = request.cookies.get("app_session")
    if sessionid != None:
        db.hdel("sessions_app", sessionid)
    return redirect(url_for('login')), 200


@app.route("/user/<string:user>", methods=[GET])
def secret(user):
    res = (1 == db.hexists(user, "passwd_hash"))
    if res:
        return {"user_exists": True}, 200
    else:
        return {"user_exists": False}, 404

@app.route('/changepasswd', methods=[POST])
def changepasswd():
    sessionid = request.cookies.get("app_session")
    log.debug(sessionid)
    if sessionid == None:
        log.debug("session id is lost")
        return redirect(url_for('login'))
    current_user = db.hget("sessions_app", sessionid)
    if current_user == None:
        log.debug("session id is bad")
        return redirect(url_for('login'))
    if request.method == POST:
        form = request.form
        username = current_user
        password = form.get("oldpassword").encode("utf-8")
        salt = db.hget(username, "passwd_salt").encode("utf-8")
        for i in range(10):
            hashed_passwd = bcrypt.hashpw(password,salt)
            password = hashed_passwd
        password = str(hashed_passwd)
        cor_password = db.hget(username, "passwd_hash")
        if password == cor_password:
            isValid, msg = validate_password(form)
            if not isValid:
                return {'msg': msg}, 400
            # password hash & save
            password = form.get("password").encode("utf-8")
            salt = bcrypt.gensalt(12)
            for i in range(10):
                hashed_passwd = bcrypt.hashpw(password,salt)
                password = hashed_passwd
            salt = str(salt)
            password = str(hashed_passwd)
            db.hset(current_user, "passwd_hash", password)
            db.hset(current_user, "passwd_salt", salt)
            return {'msg': "Pomyslnie zmieniono haslo!"}, 200
        else:
            return {'msg': "Nie udalo sie zmienic hasla!"}, 200
    else:
        {'msg': "To nie nie powinno pokazac!"}, 200

@app.route('/reset', methods=[POST, GET])
def reset():
    if request.method == POST:
        form = request.form
        username = form["username"]
        res = db.hexists(username, "data")
        if res == 0:
            return {'msg': "Taki uzytkownik nie istnieje"}
        question = db.hget(username, "question")
        return render_template("resetpasswd.html", login = username, question = question)
    else:
        return render_template("reset.html")

@app.route('/resetpasswd', methods=[POST])
def resetpasswd():
    if request.method == POST:
        form = request.form
        username = form["username"]
        res = db.hexists(username, "data")
        if res == 0:
            return {'msg': "Taki uzytkownik nie istnieje"}
        phone = form["phone"]

        user_data = db.hget(username, "data")
        user_data = json.loads(user_data)
        cor_phone = user_data["phone"]
        log.debug(cor_phone)
        log.debug(phone)
        
        if phone != cor_phone:
            return {'msg': "Nieudalo sie zresetowac hasla!"}
        answer = form.get("answer").encode("utf-8")
        salt = db.hget(username, "answer_salt").encode("utf-8")
        for i in range(10):
            hashed_answer = bcrypt.hashpw(answer,salt)
            answer = hashed_answer
        answer = str(hashed_answer)
        cor_answer = db.hget(username, "answer_hash")
        log.debug(cor_answer)
        log.debug(answer)
        if answer == cor_answer:
            # password hash & save
            generated_passwd = generatePasswd(16)
            password = generated_passwd
            salt = bcrypt.gensalt(12)
            for i in range(10):
                hashed_passwd = bcrypt.hashpw(password,salt)
                password = hashed_passwd
            salt = str(salt)
            password = str(hashed_passwd)
            db.hset(username, "passwd_hash", password)
            db.hset(username, "passwd_salt", salt)
            return {'msg': "Pomyslnie zresetowano haslo! Zaloguj sie i niezwlocznie zmien haslo na wlasne!", 'new_password': generated_passwd}
        else:
            return {'msg': "Nieudalo sie zresetowac hasla!"}
    else:
        return redirect(url_for("reset"))

@app.route("/del/<string:note>")
def delete_note(note):
    sessionid = request.cookies.get("app_session")
    log.debug(sessionid)
    if sessionid == None:
        log.debug("session id is lost")
        return redirect(url_for('login'))
    current_user = db.hget("sessions_app", sessionid)
    if current_user == None:
        log.debug("session id is bad")
        return redirect(url_for('login'))
    note_owner = db.hget(note, "owner")
    if current_user != note_owner:
        return {'msg': "Lapy precz to nie twoje!"}
    mynotes = json.loads(db.hget(current_user, "notes"))
    mynotes['notes'].remove(note)
    db.hset(current_user, "notes", json.dumps(mynotes))
    users = json.loads(db.hget(note, "users"))
    for user in users['users']:
        notesforuser = json.loads(db.hget(user, "notesforme"))
        notesforuser['notes'].remove(note)
        db.hset(user, "notesforme", json.dumps(notesforuser))
    keys = db.hkeys(note)
    for key in keys:
        db.hdel(note, key)
    db.hdel("public::notes", note)
    return redirect(url_for('notes'))
    

# ------------------------------Classes------------------------------


class Address:
    def __init__(self, street, number, postalCode, city, country):
        self.street = street
        self.number = number
        self.postalCode = postalCode
        self.city = city
        self.country = country

    def get_street(self):
        return self.street + self.number

    def get_city(self):
        return self.city

    def get_postal_code(self):
        return self.postalCode

    def get_address_str(self):
        result = "\t\t{} {}".format(self.street, self.number)
        result += "\n\t\t{} {}".format(self.postalCode, self.city)
        result += "\n\t\t{}".format(self.country)
        return result

    def address_to_dict(self):
        a = {"street": self.street, "number": self.number,
             "postalCode": self.postalCode, "city": self.city, "country": self.country}
        return a


class User:
    def __init__(self, login, fname, lname, birthDate, phone, address):
        self.login = login
        self.fname = fname
        self.lname = lname
        self.bithDate = birthDate
        self.phone = phone
        self.address = address

    def user_to_dict(self):
        u = {'login': self.login,
             'fname': self.fname,
             'lname': self.lname,
             'bithDate': self.bithDate,
             'phone': self.phone,
             'address': self.address.address_to_dict()
             }
        return u

# ------------------------------Functions------------------------------

def generatePasswd(n):
    sings = (string.ascii_letters + string.digits)
    return ''.join(random.sample(sings, n))

def removeUserSession(sessionid, delay):
    time.sleep(delay)
    db.hdel("sessions_app", sessionid)


def to_user(form):
    login = form.get("login")
    fname = form.get("firstName")
    lname = form.get("lastName")
    birthDate = form.get("birthDate")
    phone = form.get("phone")
    street = form.get("street")
    number = form.get("streetNumber")
    postalCode = form.get("postalCode")
    city = form.get("city")
    country = form.get("country")
    address = Address(street, number, postalCode, city, country)
    return User(login, fname, lname, birthDate, phone, address)


def validate_password(form):
    passwd = form.get("password")
    passwdRep = form.get("passwordRepeat")
    if passwd == None or passwd == "":
        return False, "Hasło nie może być puste!"
    elif passwd != passwdRep:
        return False, "Podane hasła są różne!"
    elif len(passwd) < 8:
        return False, "Hasło jest za krótkie!"
    else:
        passwd_regex = re.search(
            "(?=.*[!,@,#,$,%,^,&,*])(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}", passwd)
        if passwd_regex == None or passwd_regex.group() != passwd:
            return False, "Hasło nie zawiera wszystkich niezbędnych znaków!(mała litera, duża litera, cyfra, znak specjalny)"
    return True, ""


def validate_question(form):
    answer = form.get("answer")
    answerRep = form.get("answerRepeat")
    question = form.get("question")
    if answer == None or answer == "":
        return False, "Odpowiedz nie może być pusta!"
    elif answer != answerRep:
        return False, "Podane hasla sa rozne!"
    elif len(question) < 8:
        return False, "Pytanie jest za krotkie musi mieć minimum 8 znakow!"
    return True, ""


def validate_userform(form):
    res = True
    msg = ""

    # Check login
    login = form.get("login")
    isNotAvailable = (1 == db.hexists(login, "data"))
    if isNotAvailable:
        msg += "Login zajęty! Wybierz inny login!\n"
        res = False

    login_regex = re.search("[A-Z,a-z,0-9]+", login)
    if login_regex == None or login_regex.group() != login:
        msg += "Login jest niepoprawny! Musi zawierać jedynie litery bez polskich znaków i cyfry.\n"
        res = False

    # Check firstname
    firstname = form.get("firstName")
    log.debug(firstname)
    firstname_regex = re.search(
        "[A-Z,a-z,Ą,Ć,Ę,Ł,Ń,Ó,Ś,Ź,Ż,ą,ć,ę,ł,ń,ó,ś,ź,ż]+", firstname)
    if firstname_regex == None or firstname_regex.group() != firstname:
        msg += "Imię jest niepoprawne! Powinno się składać z samych liter.\n"
        res = False

    # Check lastname
    lastname = form.get("lastName")
    log.debug(lastname)
    lastname_regex = re.search(
        "[A-Z,a-z,Ą,Ć,Ę,Ł,Ń,Ó,Ś,Ź,Ż,ą,ć,ę,ł,ń,ó,ś,ź,ż]+", lastname)
    if lastname_regex == None or lastname_regex.group() != lastname:
        msg += "Nazwisko jest niepoprawne! Powinno się składać z samych liter (może być dwu członowe oddzielone znakiem -).\n"
        res = False

    # Check birthdate
    birthdate = form.get("birthDate")
    birthdate_regex = re.search("[0-9]{4}-{1}[0-9]{2}-{1}[0-9]{2}", birthdate)
    if birthdate_regex == None or birthdate_regex.group() != birthdate:
        msg += "Podana data jest niepoprawna! Jej format powinien być taki: YYYY-MM-DD! .\n"
        res = False

    # Check phone
    phone = form.get("phone")
    phone_regex = re.search("[0-9]+", phone)
    if phone_regex == None or phone_regex.group() != phone or len(phone) < 9:
        msg += "Podany numer jest niepoprawny! Powinien być liczba, miec min 9 znakow oraz nie posiadac znakow bialych!\n"
        res = False

    # Check street
    street = form.get("street")
    if street == None or street == "":
        msg += "Ulica nie może być pusta!\n"
        res = False

    # Check streetNumber
    streetNumber = form.get("streetNumber")
    if streetNumber == None or streetNumber == "":
        msg += "Numer ulicy/mieszkania nie może być pusty!\n"
        res = False
    # Check postalCode
    postalCode = form.get("postalCode")
    postalCode_regex = re.search("[0-9]{2}-{1}[0-9]{3}", postalCode)
    if postalCode_regex == None or postalCode_regex.group() != postalCode:
        msg += "Podany kod pocztowy jest niepoprawny! Jego format to: XX-XXX! .\n"
        res = False
    # Check city
    city = form.get("city")
    if city == None or city == "":
        msg += "Miasto nie może być puste!\n"
        res = False
    # Check country
    country = form.get("country")
    if country == None or country == "":
        msg += "Kraj nie może być pusty!\n"
        res = False
    return res, msg

def validate_updateuserform(form):
    res = True
    msg = ""

    # Check firstname
    firstname = form.get("firstName")
    log.debug(firstname)
    firstname_regex = re.search(
        "[A-Z,a-z,Ą,Ć,Ę,Ł,Ń,Ó,Ś,Ź,Ż,ą,ć,ę,ł,ń,ó,ś,ź,ż]+", firstname)
    if firstname_regex == None or firstname_regex.group() != firstname:
        msg += "Imię jest niepoprawne! Powinno się składać z samych liter.\n"
        res = False

    # Check lastname
    lastname = form.get("lastName")
    log.debug(lastname)
    lastname_regex = re.search(
        "[A-Z,a-z,Ą,Ć,Ę,Ł,Ń,Ó,Ś,Ź,Ż,ą,ć,ę,ł,ń,ó,ś,ź,ż]+", lastname)
    if lastname_regex == None or lastname_regex.group() != lastname:
        msg += "Nazwisko jest niepoprawne! Powinno się składać z samych liter (może być dwu członowe oddzielone znakiem -).\n"
        res = False

    # Check phone
    phone = form.get("phone")
    phone_regex = re.search("[0-9]+", phone)
    if phone_regex == None or phone_regex.group() != phone or len(phone) < 9:
        msg += "Podany numer jest niepoprawny! Powinien być liczba, miec min 9 znakow oraz nie posiadac znakow bialych!\n"
        res = False

    # Check street
    street = form.get("street")
    if street == None or street == "":
        msg += "Ulica nie może być pusta!\n"
        res = False

    # Check streetNumber
    streetNumber = form.get("streetNumber")
    if streetNumber == None or streetNumber == "":
        msg += "Numer ulicy/mieszkania nie może być pusty!\n"
        res = False
    # Check postalCode
    postalCode = form.get("postalCode")
    postalCode_regex = re.search("[0-9]{2}-{1}[0-9]{3}", postalCode)
    if postalCode_regex == None or postalCode_regex.group() != postalCode:
        msg += "Podany kod pocztowy jest niepoprawny! Jego format to: XX-XXX! .\n"
        res = False
    # Check city
    city = form.get("city")
    if city == None or city == "":
        msg += "Miasto nie może być puste!\n"
        res = False
    # Check country
    country = form.get("country")
    if country == None or country == "":
        msg += "Kraj nie może być pusty!\n"
        res = False
    return res, msg