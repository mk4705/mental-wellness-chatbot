from django.urls import path
from . import views_ui

urlpatterns = [
    path("", views_ui.new_chat, name="new_chat"),
    path("<int:session_id>/", views_ui.chat_page, name="chat_page"),
    path("<int:session_id>/delete/", views_ui.delete_chat, name="delete_chat"),
]

