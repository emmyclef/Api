import json
import uuid
import os

from flask import Blueprint, render_template, request, jsonify

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired
from Api import *
from Api.models import Movie, Series, SeriesSchema
from Api.utils import save_img
import requests
import imdb

try:
    r = requests.request("GET", "https://api.themoviedb.org/3/movie/550?api_key=03fe919b123d0ced4b33dd633638527a")
except:
    pass

# creating instance of IMDb
ia = imdb.IMDb()

api = Blueprint('api', __name__)
CHUNK_SIZE = 512

upload = Blueprint('upload', __name__)


class Movies_(FlaskForm):
    movie = FileField('Video', validators=[FileAllowed(['mp4', 'webm', 'hd'])])
    name = StringField(validators=[DataRequired()])
    submit = SubmitField('Submit ')


@upload.route('/upload/movie', methods=['GET', 'POST'])
def upload_movie():
    # data = request.get_json()
    form = Movies_()
    id = ''
    if form.validate_on_submit():
        name = str(form.name.data)
        search = ia.search_movie(name)
        for i in range(0, 1):
            # getting the id
            id = search[i].movieID
        movie = requests.get(
            f"https://api.themoviedb.org/3/movie/tt{id}?api_key=03fe919b123d0ced4b33dd633638527a&language=en-US"
        )
        CONFIG_PATTERN = 'http://api.themoviedb.org/3/configuration?api_key={key}'
        KEY = '03fe919b123d0ced4b33dd633638527a'

        url = CONFIG_PATTERN.format(key=KEY)
        r = requests.get(url)
        config = r.json()
        base_url = config['images']['base_url']
        sizes = config['images']['poster_sizes']

        def size_str_to_int(x):
            return float("inf") if x == 'original' else int(x[1:])

        filename = ''
        max_size = max(sizes, key=size_str_to_int)

        IMG_PATTERN = 'http://api.themoviedb.org/3/movie/{imdbid}/images?api_key={key}'
        r = requests.get(IMG_PATTERN.format(key=KEY, imdbid=f'tt{id}'))
        api_response = r.json()

        posters = api_response['posters']
        poster_urls = []
        for poster in posters:
            rel_path = poster['file_path']
            url = "{0}{1}{2}".format(base_url, max_size, rel_path)
            poster_urls.append(url)
        for nr, url in enumerate(poster_urls):
            r = requests.get(url)
            filetype = r.headers['content-type'].split('/')[-1]
            filename = 'poster_{0}.{1}'.format(nr + 1, filetype)
        with open(os.path.join(os.path.abspath('Api/static/movies/'), filename), 'wb') as w:
            w.write(r.content)
        movie_detail = movie.text
        dict_movie = json.loads(movie_detail)
        movie_name = save_img(form.movie.data)
        video_file = request.files['movie']
        credit = requests.get(f"https://api.themoviedb.org/3/movie/tt{id}/credits?api_key={KEY}&language=en-US")
        casts = credit.text
        lists = []
        json_casts = json.loads(casts)
        cast = json_casts['cast']
        for i in cast:
            lists.append(i['original_name'])

        description = str(dict_movie['overview'])
        review = str(dict_movie["vote_average"])
        movies = Movie()
        movies.public_id = str(uuid.uuid4())
        movies.name = str(dict_movie['original_title'])
        movies.description = description
        movies.review = review
        genres = dict_movie['genres']
        movies.cast1 = lists[0]
        movies.cast2 = lists[1]
        movies.cast3 = lists[2]
        movies.cast4 = lists[3]
        genre = []
        company = dict_movie['production_companies']
        com = []
        for i in company:
            com.append(i['name'])
        for i in genres:
            genre.append(i['name'])
        movies.genre = genre[0]
        movies.creator = com[0]
        movies.created_on = str(dict_movie['release_date'])
        movies.runtime = str(dict_movie['runtime'])
        movies.poster = filename
        movies.movies = movie_name
        movies.movie_data = video_file.read(CHUNK_SIZE)
        db.session.add(movies)
        db.session.commit()
    c = ''
    try:
        c = Movie.query.all()
    except:
        pass
    return render_template('_.html', form=form, c=c)


class Series_(FlaskForm):

    name = StringField(validators=[DataRequired()])
    submit = SubmitField('Submit ')

@upload.route('/upload/series', methods=['GET', 'POST'])
def upload_series():
    form = Movies_()
    id = ''
    if form.validate_on_submit():
        name = str(form.name.data)
        search = ia.search_movie(name)
        for i in range(0, 1):
            # getting the id
            id = search[i].movieID
        # getting information
        series = ia.get_movie(id)
        title = series.data['title']
        #writer = series.data['writer']
        total_seasons = series.data['number of seasons']
        runtimes = series.data['runtimes'][0]
        genre = series.data['genres']
        plot = series.data['plot outline']
        first_aired = series.data['year']
        ia.update(series, 'episodes')
        episodes = series.data['episodes']
        b = []
        for i in episodes.keys():

            for j in episodes[i]:
                title = episodes[i][j]['title']
                b.append(title)


        episodes_title = b
        series = Series()
        series.name = title
        series.overview = plot
        series.runtime = runtimes
        series.first_aired_on = first_aired
        series.public_id = str(uuid.uuid4())
        series.genre = genre
        series.total_seasons = total_seasons

        series.episode = episodes_title
        db.session.add(series)
        db.session.commit()

    c = ''
    try:
        c = Series.query.all()
    except:
        pass
    return render_template('series.html',form=form, c=c)


@upload.route('/series')
def seri():
    series = Series.query.all()
    series_schema = SeriesSchema(many=True)
    result = series_schema.dump(series)
    return jsonify({'data': result})