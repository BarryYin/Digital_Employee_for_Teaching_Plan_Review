from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import logging
import re
from datetime import datetime
from xfagent import review_lesson_plan
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session管理
logger = logging.getLogger(__name__)

# 数据库连接函数
def get_db_connection():
    conn = sqlite3.connect('english_writing.db')
    conn.row_factory = sqlite3.Row
    return conn


def count_input_tokens(text):
    """Count English words plus CJK chars for consistent frontend/backend behavior."""
    content = text or ''
    english_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", content)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", content)
    return len(english_words) + len(cjk_chars)


def build_suggestions(value):
    if not value:
        return []

    text = (value or '').strip()
    if not text:
        return []

    text = re.sub(r'^```(?:markdown|md)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = re.sub(
        r'(?:^|[\n\r])#{1,6}\s*(?:综合改进建议|改进建议|建议|优先改进建议)\s*',
        '\n',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(?<=[；;。])\s*(?=(?:\d+[\.、)]|[一二三四五六七八九十]+[、.]))',
        '\n',
        text,
    )

    lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    suggestions = []
    current = None
    has_numbered_items = bool(
        re.search(r'(^|[\n\r；;\s])(?:\d+[\.、)]|[一二三四五六七八九十]+[、.])\s*', text)
    )
    has_bullet_items = bool(re.search(r'(^|[\n\r])\s*[-*+]\s+', text))

    def normalize_suggestion_item(item):
        cleaned = item.strip()
        cleaned = re.sub(r'^(?:[-*+]\s+|\d+[\.、)]\s*|[一二三四五六七八九十]+[、.]\s*)', '', cleaned)
        cleaned = re.sub(r'[*_`#>]+', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'[；;]\s*$', '', cleaned)
        return cleaned

    for line in lines:
        if re.fullmatch(r'[-|:\s]+', line):
            continue
        if re.match(r'^#{1,6}\s*', line):
            continue

        is_numbered_item = re.match(r'^(?:\d+[\.、)]\s*|[一二三四五六七八九十]+[、.]\s*)', line)
        is_bullet_item = re.match(r'^[-*+]\s+', line)

        if is_numbered_item or (is_bullet_item and not has_numbered_items and has_bullet_items):
            if current:
                suggestions.append(normalize_suggestion_item(current))
            current = line
            continue

        if current:
            current += ' ' + normalize_suggestion_item(line)
        else:
            suggestions.append(normalize_suggestion_item(line))

    if current:
        suggestions.append(normalize_suggestion_item(current))

    suggestions = [item for item in suggestions if item]
    if suggestions:
        return suggestions

    plain_text = re.sub(r'[*_`#>]+', '', text).strip()
    return [plain_text] if plain_text else []


def extract_suggestion_block(text):
    content = (text or '').strip()
    if not content:
        return ''

    patterns = (
        r'(?:^|\n)#{1,6}\s*(?:[一二三四五六七八九十]+[、.]\s*)?(?:综合改进建议|优先改进建议|改进建议)\s*(.*?)(?=\n(?:---\s*)?\n#{1,6}\s*|\Z)',
        r'(?:综合改进建议|优先改进建议|改进建议)[：:]\s*(.*?)(?=\n(?:总结|结语|结论)|\Z)',
    )

    for pattern in patterns:
        match = re.search(pattern, content, flags=re.S | re.I)
        if match:
            return match.group(1).strip()

    return ''


def resolve_suggestions(improvement_suggestions, overall_comment=''):
    suggestions = build_suggestions(improvement_suggestions)
    fallback_block = extract_suggestion_block(overall_comment)
    fallback_suggestions = build_suggestions(fallback_block)

    if fallback_suggestions and len(fallback_suggestions) > len(suggestions):
        return fallback_suggestions

    return suggestions

# 初始化数据库
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 创建评审记录表
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
    error_message = request.args.get('error', '')
    return render_template('index.html', error_message=error_message)
    


@app.route('/submit_essay', methods=['POST'])
def submit_essay():
    title = (request.form.get('title') or '').strip()
    grade = (request.form.get('grade') or '').strip()
    content = request.form.get('content')

    if not title or not grade or not content:
        return redirect(url_for('index', error='请完整填写教案标题、教案年级和教案内容后再提交。'))
    
    # Keep counting logic aligned with frontend to avoid mismatch.
    word_count = count_input_tokens(content)
    
    try:
        score, review_result, suggestion = review_lesson_plan(title, grade, content)
        if score is None:
            raise ValueError('评分结果为空')

        # 兼容返回字符串分数
        score = int(score)
       
        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO essays (title, content, grade, word_count, score, overall_comment, improvement_suggestions, submission_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (title, content, grade, word_count, score, review_result, suggestion, datetime.now().strftime('%Y-%m-%d'))
        )
        conn.commit()
        essay_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        logger.exception(
            "Submit lesson plan failed | title=%s grade=%s word_count=%s",
            title,
            grade,
            word_count,
        )
        return redirect(url_for('index', error='教案提交失败：评审服务暂时不可用，请稍后重试。'))
    
    return redirect(url_for('review_result', essay_id=essay_id))

@app.route('/review_result/<int:essay_id>')

def review_result(essay_id):
    # 从数据库中查找对应的评审记录
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for('index'))
    
    essay = dict(row)
    
    score = essay['score']
    if score >= 90:
        level = '优秀'
        level_description = '教案设计完整清晰，教学逻辑和课堂组织都很扎实。'
    elif score >= 80:
        level = '良好'
        level_description = '教案整体表现不错，局部细节还有进一步打磨空间。'
    elif score >= 70:
        level = '中等'
        level_description = '教案基本符合要求，建议继续加强活动设计和目标对齐。'
    elif score >= 60:
        level = '及格'
        level_description = '教案达到基本要求，但仍有较大的优化空间。'
    else:
        level = '不及格'
        level_description = '教案尚未达到预期标准，建议进一步完善教学设计。'
    
    return render_template('review_result.html',
                           score=essay['score'],
                           level=level,
                           level_description=level_description,
                           overall_comment=essay['overall_comment'],
                           suggestions=resolve_suggestions(
                               essay['improvement_suggestions'],
                               essay['overall_comment'],
                           ),
                           lesson_title=essay['title'],
                           lesson_content=essay['content'],
                           word_count=essay['word_count'],
                           essay_date=essay['submission_date'],
                           lesson_grade=essay['grade'])


@app.route('/history')
def history():
    # 从数据库中获取所有评审记录，按提交日期降序排列
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays ORDER BY submission_date DESC, id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    essays = []
    for row in rows:
        essay = dict(row)
        essays.append(essay)
    
    return render_template('history.html', essays=essays)

@app.route('/history/detail/<int:essay_id>')
def history_detail(essay_id):
    # 从数据库中查找对应的评审记录
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for('history'))
    
    essay = dict(row)
    essay['suggestions'] = resolve_suggestions(
        essay.get('improvement_suggestions'),
        essay.get('overall_comment'),
    )
    
       
    return render_template('history_detail.html', essay=essay)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    app.run(host="0.0.0.0", port=5000, debug=True)
