from flask import Flask

from routes_basic import bp as basic_bp
from routes_analysis import bp as analysis_bp
from routes_ai import bp as ai_bp

# ============ Flask 应用初始化 ============
app = Flask(__name__)


@app.after_request
def _add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response


# 数据导入仅在显式调用时执行（由路由或管理命令触发），启动时不自动初始化。

app.register_blueprint(basic_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(ai_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
