from pathlib import Path

from flask import Flask, render_template, request, send_from_directory


app = Flask(__name__)
SOLID_STATE_DIR = Path(__file__).resolve().parent / 'html5up-solid-state'


@app.route('/')
def home_page():
    return render_template('index.html')


@app.route('/mastering-services')
def mastering_services_page():
    return render_template(
        'mastering_services.html',
        entered_from_home=request.args.get('from_home') == '1',
    )


@app.route('/mastering-services-assets/<path:asset_path>')
def mastering_services_asset(asset_path):
    return send_from_directory(SOLID_STATE_DIR, asset_path)


if __name__ == '__main__':
    app.run(debug=True)
