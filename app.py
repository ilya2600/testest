from flask import Flask, render_template, request, redirect

app = Flask(__name__)

import sqlite3

import dotenv
from dotenv import load_dotenv
import os

load_dotenv()

PAGE_PATH = os.getenv('PAGE_PATH')

def init():
    conn = sqlite3.connect("data.db")
    conn.execute("CREATE TABLE IF NOT EXISTS notepad (content)")
    
    hasRow = conn.execute("SELECT content FROM notepad")
    if not hasRow.fetchone():
        conn.execute("INSERT INTO notepad VALUES ('default text')")
    
    conn.commit()
    conn.close()
    
init()

@app.route("/help")
def helpinfo():
    return "Полезная Информация!!!"


'''
<style>
    .table{
        background: lightblue;
        border: solid gray 2px;
        font-size: 24px;
        text-align: center;
    }
    .row {
        display: flex;
    }
    .col {
        flex: 1;
        border: solid gray 2px;
        padding: 5px;
    }
    form {
        display: flex;
    }
    input{
        flex: 1;
        height: 28px;
        font-size: 24px;
    }
    button {
        font-size: 24px;
    }
</style>
'''

'''
<div class="table">
    <div class="row">
        <div class="col"></div>
    </div>
</div>

'''

@app.route(PAGE_PATH)
def show_db():
    conn = sqlite3.connect("data.db")
    content = conn.execute("SELECT content FROM notepad").fetchone()[0]
        
    conn.close()
    return render_template('notepad.html',content=content)

@app.route("/save", methods=['POST'] )
def save():
    content = request.form['content']
    
    conn = sqlite3.connect("data.db")
    conn.execute("UPDATE notepad SET content='" + content +"'")
    conn.commit()
    conn.close()
    return redirect(PAGE_PATH)

@app.route("/cmd_sql", methods=['POST'] )
def cmd_sql():
    sql = request.form['sql']
    
    conn = sqlite3.connect("data.db")
    conn.execute(sql)
    conn.commit()
    conn.close()
    return sql

    
if __name__ == "__main__":
    app.run(debug=True)
    
    