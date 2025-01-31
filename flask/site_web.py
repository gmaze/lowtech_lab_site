#////////////////////////////IMPORTATION//////////////////////////////////

from flask import Flask, render_template, url_for, redirect, request, session,flash,jsonify
import threading
import re
import sqlite3
from werkzeug.exceptions import abort
from waitress import serve
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
import os
import time
import psutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#//////////////////////////////////////////////////////////////////////////
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = '7z3V98deMEiYRfF2x4i9'
#////////////////////////////////////CONNECTION BDD////////////////////////
connection = sqlite3.connect('database.db',check_same_thread=False)
curseur = connection.cursor()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)  
    return post


def valeur():
    while True:
        total_memory, used_memory, free_memory = map(int, os.popen('free -t -m').readlines()[-1].split()[1:])
        mem=round((used_memory/total_memory) * 100, 2)
        cpuload = psutil.cpu_percent(interval=1)
        curseur.execute('INSERT INTO monitoring (cpu, mem) VALUES (?,?)',(cpuload, mem))
        connection.commit()
        time.sleep(2)
#////////////////////////////////////////////////////////////////////////////////LOGIN///////////////////////////////

@app.route('/login',methods=['GET','POST'])
def login():
    # créer une variable pour stocker les erreur dedans par la suite
    msg=''
    # verifie que les champs sont remplie
    if request.method == 'POST' and 'email' in request.form and 'mdp' in request.form:
        # pour récupérer plus simplement 
        email = request.form['email']
        mdp = request.form['mdp']
        #chercher si le compte existe
        curseur.execute("SELECT * FROM users WHERE email = '{}' ".format(email))
        # retourner les valeurs
        account= curseur.fetchone()
        # print(account)
        # print(account[4])
        # print(check_password_hash(account[4],mdp))
        if account :
            if check_password_hash(account[4],mdp) == True:
                # SI le compte existe
                # creer une session
                session['loggedin'] = True
                session['id'] = account [0]
                session ['username'] = account [3]
                return redirect(url_for('blog'))
        else: 
            #Compte n'existe pas ou mdp pas correct
            msg='Email ou Mot de passe INCORRECT'
    return render_template('connecter.html',msg=msg)
#//////////////////////////////////////////////////////////////////////////////////REGISTER///////////////////////////////////
@app.route('/register', methods=['GET','POST'])
def register():
    msg=''
    if request.method == 'POST' and 'email' in request.form and 'nom' in request.form and 'prenom' in request.form and 'mdp' in request.form:
        email = request.form['email']
        nom = request.form['nom']
        prenom = request.form['prenom']
        mdp = request.form['mdp']
        hmdp=generate_password_hash(mdp, method='pbkdf2:sha1', salt_length=8)
        curseur.execute("SELECT * FROM users WHERE email = '{}' ".format(email))
        account= curseur.fetchone()
        if account:
            msg = 'Le compte existe déjà'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Email invalide'
        elif not nom or not prenom or not mdp or not email:
            msg = 'Remplir le forulaire !'
        else:
            # Si le compte n'existe pas 
            curseur.execute("INSERT INTO users VALUES (NULL,'{}','{}','{}','{}','{}')".format(nom,prenom,email,hmdp,'internaute'))
            connection.commit()
            msg='Compte enregistré'
            return redirect("login")
    elif request.method == 'POST':
        #si le formulaire est vide
        msg= "Remplir tous les champs !"
    return render_template('inscription.html', msg=msg)
#//////////////////////////////////////////////////////////////////////////////////////LOGOUT//////////////////////
@app.route('/logout')
def logout():
    #supprimer les données de sessions
    session.pop('loggedin',None)
    session.pop('id',None)
    session.pop('username',None)
    session.clear()
    print("session supprimer")
    return redirect(url_for('login'))
#///////////////////////////////////////////////////////////////////////////////////////HOME///////////////////////////
@app.route('/')
def home():
    database_path = 'database.db' # chemin de la base de données
    conn = sqlite3.connect(database_path) # connexion à la base de données
    cursor = conn.cursor() # création du curseur
    cursor.execute('SELECT Pourcentage_BAT FROM VALEURS_CAPTEURS ORDER BY date_jour DESC LIMIT 1') # requête SQL d'acquisition des données de batterie en fonction de la date pour obtenir le plus récent
    row = cursor.fetchone()

    if row is not None:
        pourcent = row[0] # row[0] stoque désormais la valeur prise dans la bdd
    else:
        pourcent = 0

    cursor.close()
    conn.close()
    return render_template('index.html', pourcent_battery_recupere=pourcent)





@app.route('/changer_etat')
def changer_etat():
    etat = request.args.get('etat')
    
    if etat == 'true':
        print("l'etat:", etat)
        #ici requete SQL pour mettre l'etat des image en haute qualité
    else:
        print("l'etat:", etat)
        #ici requete SQL pour mettre l'etat des image en basse qualité

    return jsonify({'etat': etat})


#//////////////////////////////////////////////////////////////////////////////////////////GRAPHIQUE/////////////////////////
@app.route('/graphique')
def graphique():
    
    cpu = curseur.execute('SELECT cpu from monitoring;').fetchall()
    mem = curseur.execute('SELECT mem from monitoring;').fetchall()
    cpu1= list(cpu[-1])
    mem1 = list(mem[-1])
    pourcent_bat = curseur.execute('SELECT Pourcentage_BAT from VALEURS_CAPTEURS;').fetchall()
    extracted_list_bat = [item for tuple_ in pourcent_bat for item in tuple_]
    bat_affiche = []
    for i in range(5):
        bat_affiche.append(extracted_list_bat[-1 - i])
    print("valeur affiche batterie ---->", bat_affiche)
    
    date = curseur.execute('SELECT date_jour from VALEURS_CAPTEURS;').fetchall()
    date1 = []
    for i in range(5):
        date1.append(list(date[-1 - i]))
    date_liste = [x[0] for x in date1]
    print("c'est la date ---->", date_liste)

    fig, ax1 = plt.subplots()
    ax1.plot(date_liste,bat_affiche)
    ax1.set_xlabel('Dates')
    ax1.set_ylabel('Pourcentage')
    ax1.set_title('Graphique 1')
    
    fig.autofmt_xdate()
    fichier = 'static/ressource/graph/graph_bat.png'
    plt.savefig(fichier)
    permissions = 0o777
    os.chmod(fichier, permissions)
    courant = curseur.execute('SELECT Courant from VALEURS_CAPTEURS;').fetchall()
    extracted_list_courant = [item for tuple_ in courant for item in tuple_]
    courant_affiche=[]
    for i in range (5):
        courant_affiche.append(extracted_list_courant[-1 - i])
    print("valeur afficher courant ---->",courant_affiche)

    fig, ax2 = plt.subplots()
    ax2.plot(date_liste,courant_affiche)
    ax2.set_xlabel('Dates')
    ax2.set_ylabel('Courant')
    ax2.set_title('Graphique 2')
    
    fig.autofmt_xdate()
    fichier = 'static/ressource/graph/graph_courant.png'
    plt.savefig(fichier)
    os.chmod(fichier, permissions)
    
    print("---------------------------------------------------------------------------------")
    return render_template('graphique.html', mem = mem1[0], cpuload = cpu1[0])

#//////////////////////////////////////////////////////////////////////////////////////////A PROPOS/////////////////
@app.route('/a_propos')
def a_propos():
    return render_template('a_propos.html')
#/////////////////////////////////////////////////////////////////////////////////////////////BLOG//////////////////////////
@app.route('/blog')
def blog():
    autorisation = False # détermini si c'est un administrateur ou pas 
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    try:
        curseur.execute("SELECT * FROM users WHERE email = '{}' ".format(session.get('username')))
        account= curseur.fetchone()
        print (account[5])
        if account[5]=='admin':
            autorisation = True
    finally:
        return render_template('blog.html', posts=posts, autorisation = autorisation)


#/////////////////////////////////////////////////////////c//////////////////////////////////////CREATE////////////////////////
@app.route('/create', methods=('GET', 'POST'))
def create():
    if session.get('username',False):
        curseur.execute("SELECT * FROM users WHERE email = '{}' ".format(session.get('username')))
        account= curseur.fetchone()
        print(account)
        if account[5]=='admin':
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                miniature = request.files['miniature']
                # annexe = request.files['annexe']

                if not title:
                    flash('Titre requie!')
                else:
                    filename = secure_filename("miniature."+title+".png")
                    emplacement="/static/photos/miniature/" + filename
                    miniature.save('./static/photos/miniature/' + filename)
                    conn = get_db_connection()
                    conn.execute('INSERT INTO posts (title, content, miniature) VALUES (?,?,?)',(title, content,emplacement))
                    conn.commit()
                    conn.close()
                    return redirect(url_for('blog'))
            return render_template('create.html')
        else:
            return redirect(url_for('blog'))
    else:
        return redirect(url_for('login'))
#/////////////////////////////////////////////////////////////////////////////////////////////////POST////////////////
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)
#////////////////////////////////////////////////////////////////////////////////////////////////EDIT/////////////////
@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    try:
        curseur.execute("SELECT * FROM users WHERE email = '{}' ".format(session.get('username')))
        account= curseur.fetchone()
        print(account)
        if account[5]=='admin':
            post = get_post(id)
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                if not title:
                    flash('Titre requit !')
                else:
                    conn = get_db_connection()
                    conn.execute('UPDATE posts SET title = ?, content = ?'
                                ' WHERE id = ?',
                                (title, content, id))
                    conn.commit()
                    conn.close()
                    return redirect(url_for('blog'))
            return render_template('edit.html', post=post)
    except:
        return redirect(url_for('login'))
#//////////////////////////////////////////////////////////////////////////////////////////DELETE//////////////////////
@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" Supprimer avec succès !'.format(post['title']))
    return redirect(url_for('blog'))
#//////////////////////////////////////////////////////////////////////////////////////////TEST//////////////////////
@app.route('/test')
def get():
    return session.get('username','not set')
    #return render_template('test.html')


#//////////////////////////////////////////////////////////////////////////TEST2//////////
# upload_folder = os.path.join('static', 'photos/miniature/')
# app.config['UPLOAD'] = upload_folder


if __name__ == "__main__":
    # app.run(host="0.0.0.0", debug=True)
    # with app.app_context():
    #     t1 = threading.Thread(target=valeur)
    #     t1.start()

    print("Adresse du site: http://127.0.0.1:5012")
    print("Le site est accessible depuis son ip local aussi.")
    print("En cours d'exécution...")
    serve(app, host='0.0.0.0', port= 5012)
    # serve(app, host='0.0.0.0')
