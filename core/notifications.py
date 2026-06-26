SESSION_KEY = "zreal_notifications"


def push_notification(request, level, message):
    notification = {"level": level, "message": message}
    notifications = request.session.get(SESSION_KEY, [])
    notifications.append(notification)
    request.session[SESSION_KEY] = notifications[-20:]
    request.session.modified = True
    return notification


def drain_notifications(request):
    notifications = request.session.get(SESSION_KEY, [])
    if notifications:
        request.session[SESSION_KEY] = []
        request.session.modified = True
    return notifications
