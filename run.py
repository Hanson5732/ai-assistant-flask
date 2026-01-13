from app import create_app

app = create_app()

# 注册路由
app.route('/api/process-paper', methods=['POST'])(process_paper)



if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')