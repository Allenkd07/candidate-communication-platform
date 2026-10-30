from django.urls import path

from .views import MessageDetailApi, MessageSendApi

urlpatterns = [
    path("messages", MessageSendApi.as_view(), name="message-send"),
    path("messages/<str:message_id>", MessageDetailApi.as_view(), name="message-detail"),
]
