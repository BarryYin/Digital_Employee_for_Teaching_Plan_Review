from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import os
import sqlite3
from datetime import datetime
from xfagent import create_writting_topic, review_writting
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session管理

# 数据库连接函数
def get_db_connection():
    conn = sqlite3.connect('english_writing.db')
    conn.row_factory = sqlite3.Row
    return conn

# 初始化数据库
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 创建作文表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS essays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        grade TEXT NOT NULL,
        word_count INTEGER NOT NULL,
        score INTEGER NOT NULL,
        overall_comment TEXT,
        improvement_suggestions TEXT,
        submission_date TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()



@app.route('/')
def index():
    # 确保session中有关键信息
    if 'current_topic' not in session:
        session['current_topic'] = ''
    return render_template('index.html', current_topic=session.get('current_topic', ''))

@app.route('/generate_topic', methods=['POST'])
def generate_topic():
    grade = request.form.get('grade')
    try:
        topic = create_writting_topic(grade)
        session['current_topic'] = topic
        session['current_grade'] = grade
        return jsonify({'topic': topic})
    except:
        return jsonify({'error': '创建作文题目失败'}), 400
    


@app.route('/submit_essay', methods=['POST'])
def submit_essay():
    content = request.form.get('content')
    topic = session.get('current_topic')
    grade = session.get('current_grade')
    
    if not content or not topic:
        return redirect(url_for('index'))
    
    # 简单的单词计数（以空格分隔）
    word_count = len(content.strip().split())
    
    try:
        #score ,review_result,suggestion= review_writting("The Food That Brings Back Memories?","this is a test content")
        score, review_result, suggestion = review_writting(topic, content)
        print(score, review_result, suggestion)
       
        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO essays (title, content, grade, word_count, score, overall_comment, improvement_suggestions, submission_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (topic, content, grade, word_count, score, review_result, suggestion, datetime.now().strftime('%Y-%m-%d'))
        )
        conn.commit()
        essay_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        print(f"Error submitting essay: {e}")
        return jsonify({'error': '作文评审或保存失败'}), 400    
    
    return redirect(url_for('review_result', essay_id=essay_id))

@app.route('/review_result/<int:essay_id>')

def review_result(essay_id):
    # 从数据库中查找对应的作文
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for('index'))
    
    # 将数据库行转换为字典
    essay = dict(row)
    
    # 根据分数确定等级和描述
    score = essay['score']
    if score >= 90:
        level = '优秀'
        level_description = '您的作文质量非常高，表达准确，逻辑清晰！'
    elif score >= 80:
        level = '良好'
        level_description = '您的作文整体表现不错，有一些小的改进空间。'
    elif score >= 70:
        level = '中等'
        level_description = '您的作文基本符合要求，需要在某些方面加强。'
    elif score >= 60:
        level = '及格'
        level_description = '您的作文刚刚达到及格水平，有较大的提升空间。'
    else:
        level = '不及格'
        level_description = '您的作文尚未达到要求，建议多练习并寻求指导。'
    
    # 将数据直接传递给模板
    return render_template('review_result.html',
                           score=essay['score'],
                           level=level,
                           level_description=level_description,
                           overall_comment=essay['overall_comment'],
                           suggestions=[essay['improvement_suggestions']] if essay['improvement_suggestions'] else [],
                           topic=essay['title'],
                           essay_content=essay['content'],
                           word_count=essay['word_count'],
                           essay_date=essay['submission_date'])


@app.route('/history')
def history():
    # 从数据库中获取所有作文，按提交日期降序排列
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays ORDER BY submission_date DESC')
    rows = cursor.fetchall()
    conn.close()
    
    # 将数据库行转换为字典列表
    essays = []
    for row in rows:
        essay = dict(row)
        essays.append(essay)
    
    return render_template('history.html', essays=essays)

@app.route('/history/detail/<int:essay_id>')
def history_detail(essay_id):
    # 从数据库中查找对应的作文
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for('history'))
    
    # 将数据库行转换为字典，并解析JSON格式的改进建议
    essay = dict(row)
    #essay['improvement_suggestions'] = json.loads(essay['improvement_suggestions'])
    
       
    return render_template('history_detail.html', essay=essay)

if __name__ == '__main__':
    app.run(debug=True)