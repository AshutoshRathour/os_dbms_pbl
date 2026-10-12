"""Main view routes — serves HTML pages."""

from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@main_bp.route('/jobs')
@login_required
def jobs_page():
    return render_template('jobs/list.html')


@main_bp.route('/jobs/submit')
@login_required
def submit_job_page():
    return render_template('jobs/submit.html')


@main_bp.route('/jobs/<int:job_id>')
@login_required
def job_detail_page(job_id):
    return render_template('jobs/detail.html', job_id=job_id)


@main_bp.route('/nodes')
@login_required
def nodes_page():
    return render_template('nodes.html')


@main_bp.route('/scheduling')
@login_required
def scheduling_page():
    return render_template('scheduling.html')
