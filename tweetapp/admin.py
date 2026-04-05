from django.contrib import admin
from tweetapp.models import Tweet, TweetImage
from django.utils.html import format_html
from tweetapp.models import PatchNote, ChatThread, Message


class TweetImageInline(admin.TabularInline):
    model = TweetImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:100px;">', obj.image.url)
        return ""

class TweetAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Nickname Group', {"fields": ["nickname"]}),
        ('Message Group', {"fields": ["message"]}),
    ]
    list_display = ['nickname', 'message', 'created_at']
    inlines = [TweetImageInline]

admin.site.register(Tweet, TweetAdmin)


@admin.register(PatchNote)
class PatchNoteAdmin(admin.ModelAdmin):
    list_display = ['version', 'title', 'created_at']

@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated_at', 'theme_color']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'thread', 'sender', 'content', 'created_at']