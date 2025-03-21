from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection

customer = Blueprint('customer', __name__, template_folder='templates', static_folder='static')
