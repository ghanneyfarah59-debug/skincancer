from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1 style="color:green">✅ APPLICATION FONCTIONNELLE !</h1>
    <p>Votre serveur Flask tourne correctement sur le port 5000</p>
    <p>Test réussi !</p>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=5000)