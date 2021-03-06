import uuid
from flask import *
from flask_cors import cross_origin
from flask_login import current_user, login_required
from flask_socketio import emit, close_room, leave_room, join_room

from Api import *
from Api.models import Room, RoomSchema, Users, Friend, FriendSchema, Movie, Vote

chat = Blueprint('chat', __name__)

store = []


# adding a friend to watch with
@chat.route('/api/add/friend/<string:name>', methods=["GET", 'POST'])
@cross_origin()
@login_required
def add(name):
    add_friend = Users.query.filter_by(name=name).first()
    add_req = Users.query.filter_by(name=current_user.name).first()
    if add_friend:
        friends = Friend.query.filter_by(get=current_user). \
            filter_by(u_friend=add_friend.name).first()
        if friends:
            return jsonify(
                {
                    "message": f" you are already friends with {add_friend.name}"
                }
            )
        else:
            if add_friend.name == current_user.name:
                return jsonify(
                    {
                        "message": "You cannot add your self"
                    }
                )

            c_user = Friend(get=current_user, u_friend=add_friend.name)
            added_user = Friend(get=add_friend, u_friend=current_user.name)
            db.session.add(c_user)
            db.session.add(added_user)
            db.session.commit()
        return jsonify(
            {"message": f"{add_req.name} is now friends with {add_friend.name}"
             })
    return jsonify(
        {
            'message': f"{name} not found"
        }
    )


@chat.route('/api/remove/friend/<string:name>', methods=["GET", 'POST'])
@cross_origin()
@login_required
def remove_(name):
    remove_friend = Users.query.filter_by(name=name).first()
    add_req = Users.query.filter_by(name=current_user.name).first()
    if remove_friend:
        friends = Friend.query.filter_by(get=current_user). \
            filter_by(u_friend=remove_friend.name).first()
        if not friends:
            return jsonify(
                {
                    "message": f" you are not friends with {remove_friend.name}"
                }
            )
        else:
            if remove_friend.name == current_user.name:
                return jsonify(
                    {
                        "message": "You cannot unfriend your self"
                    }
                )
            c_user = Friend.query.filter_by(get=current_user, u_friend=remove_friend.name).first()
            added_user = Friend.query.filter_by(get=remove_friend, u_friend=current_user.name).first()
            db.session.delete(c_user)
            db.session.delete(added_user)
            db.session.commit()
        return jsonify(
            {"message": f"{add_req.name} is no more friends with {remove_friend.name}"
             })
    return jsonify(
        {
            'message': f"{name} not found"
        }
    )


# all friends of a particular user
@chat.route('/api/my/friends', methods=['GET'])
@cross_origin()
@login_required
def my_friends():
    friends = Friend.query.filter_by(get=current_user).all()
    friend_schema = FriendSchema(many=True)
    result = friend_schema.dump(friends)
    return jsonify(
        {
            "data": result
        }
    )


# all friends of all users
@chat.route("/all/friends")
def all_frnds():
    f = Friend.query.all()
    friend_schema = FriendSchema(many=True)
    result = friend_schema.dump(f)
    return jsonify(
        {
            "data": result
        }
    )


# Create room
@chat.route('/api/create/room/for/<string:movie>', methods=['POST'])
@cross_origin()
@login_required
def create_room(movie):
    created_room = str(uuid.uuid4())
    movie = Movie.query.filter_by(public_id=movie).first()
    host = current_user.name
    room = Room()
    room.unique_id = created_room
    room.host = host
    room.admin = True
    db.session.add(room)
    db.session.commit()

    '''return jsonify(
        {
            "message": f"Room {created_room} created by {host} ",
            "movie": movie.movies,
            "movie name": movie.name
        }
    )'''
    return redirect(url_for('chat.watch', movie=movie.public_id, room=created_room))


# redirecting to the room id
@chat.route('/api/watch/<string:movie>/in/room/<string:room>', methods=['GET'])
@login_required
def watch(movie, room):
    movie = Movie.query.filter_by(public_id=movie).first()
    room = Room.query.filter_by(unique_id=room).first()
    store.append(room.unique_id)
    return jsonify(
        {

            "movie": movie.movies,
            "movie name": movie.name,
            'room': room.unique_id,
            'image': movie.poster
        }
    )


@chat.route('/api/active/', methods=['GET'])
@login_required
def active():
    active_friend=[]
    active = []
    friends = Friend.query.filter_by(get=current_user).all()
    friend_schema = FriendSchema(many=True)
    result = friend_schema.dump(friends)
    for value in result:
        for i,v in value.items():
            if i == 'u_friend':
                active.append(v)
    for f in active:
        if 'jake' in f:
            active_friend.append(f)

    return jsonify({
        'active': active_friend
    })


@chat.route('/api/my/rooms', methods=['GET'])
@cross_origin()
@login_required
def my_rooms():
    room = Room.query.filter_by(host=current_user.name).all()
    room_schema = RoomSchema(many=True)
    result = room_schema.dump(room)
    return jsonify(
        {
            "data": result
        }
    )


@chat.route('/api/my/rooms/delete/<string:room_id>', methods=['POST'])
@cross_origin()
@login_required
def delete_room(room_id):
    room = Room.query.filter_by(host=current_user.name).filter_by(unique_id=room_id).first()
    if room:
        db.session.delete(room)
        db.session.commit()
        return jsonify(
            {
                "data": f"{room.unique_id} deleted"
            }
        )
    return jsonify(
        {
            "message": "error"
        }
    )


## socket server
##########################################


@io.on("connect", namespace='/chat')
def on_connect(data):

    return jsonify({'message': 'connected'})


@io.on('disconnect', namespace='/chat')
def disconnect():
    return jsonify({'message': 'disconnected'})


@io.on_error(namespace='/room')
def chat_error_handler(e):
    print('An error has occurred: ' + str(e))


@io.on('my event')
def handle_event(json):
    print('recieved' + str(json))
    io.emit('response', json)


@io.on('online')
def online(data):
    active = []
    online_friend=[]
    friends = Friend.query.filter_by(get=current_user).all()
    friend_schema = FriendSchema(many=True)
    result = friend_schema.dump(friends)
    for value in result:
        for i, v in value.items():
            if i == 'u_friend':
                active.append(v)
    for f in active:
        if data['data'] in f:
            online_friend.append(f)

    emit('status_change', {'username': online_friend, 'status': 'online'}, broadcast=True)







@io.on("offline")
def offline(data):
    emit('status_change', {'username': data['username'], 'status': 'offline'}, broadcast=True)


@io.on('Offer')
def SendOffer(offer):
    emit('BackOffer', offer)


@io.on('Answer')
def SendAnswer(data):
    emit('BackAnswer', data)


# join room
@io.on("join_user")
def on_new_user(data):
    room = data['data']
    print(data)
    active = Room.query.filter_by(unique_id=room).first()
    print(active.unique_id)
    name = current_user.name
    join_room(active.unique_id)
    emit("new_user", {"name": name, room: room}, room=active.unique_id, broadcast=True)


@io.on('my event')
def handle_event(json):
    print('recieved' + str(json))
    io.emit('response', json)


# leave room
@io.on("leave_user", namespace='/chat')
def on_leave_room(data):
    room = data['data']
    active = Room.query.filter_by(unique_id=room).first()
    name = current_user.name
    leave_room(active.unique_id)
    emit("New user", {"name": name}, room=active.unique_id, broadcast=True)
    redirect(url_for("api.home"))


# close room
@io.on("close_room", namespace='/chat')
def on_close_room(data):
    room = data['data']
    active = Room.query.filter_by(host=current_user.name) \
        .filter_by(admin=True) \
        .filter_by(unique_id=room).first()
    close_room(active.unique_id)
    db.session.delete(active.unique_id)
    redirect(url_for("api.home"))


@io.on("video_chat", namespace='/chat')
def on_video_chat(data):
    room = request.get_json()
    active = Room.query.filter_by(unique_id=room['room']).first()
    pass


global clients

io.on('NewClient')


def newclient():
    clients = 0
    if clients < 2:
        if clients == 1:
            io.emit('CreatePeer')
    else:
        io.emit('SessionActive')
    clients = clients + 1


# watch movie
@io.on("watch_movie", namespace='/chat')
def on_video_stream(data):
    room = data['data']
    active = Room.query.filter_by(unique_id=room).first()
    host = active.host
    movie_ = Movie.query.filter_by(public_id=room['u_id']).first()
    emit("Watch", {
        "host": host,
        "movie": movie_.movies,
    }, room=active.unique_id, broadcast=True)


# send message
@io.on("post_message", namespace='/chat')
def on_new_message(message):
    room = message['data']
    data = request.get_json()
    active = Room.query.filter_by(unique_id=room).first()
    emit("New message", {
        "sender": current_user.name,
        "time": datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
        "data": data['message'],
    }, room=active.unique_id, broadcast=True)


@io.on('vote')
def handleVote(ballot):
    vote = Vote(votes=ballot)
    db.session.add(vote)
    db.session.commit()

    result1 = Vote.query.filter_by(votes=1).count()
    result2 = Vote.query.filter_by(votes=2).count()

    emit('vote_result', {'result1': result1, 'result2': result2}, broadcast=True)
