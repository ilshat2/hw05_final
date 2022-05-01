from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.conf import settings
from django.views.decorators.cache import cache_page

from posts.models import Post, Group, User, Follow
from posts.forms import PostForm, CommentForm


@cache_page(20)
def index(request: HttpRequest) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон index.html.
    """
    title = 'Последние обновления на сайте'
    post_list = Post.objects.select_related('group')
    paginator = Paginator(post_list, settings.MAX)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'title': title,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request: HttpRequest, slug: str) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон group_list.html.
    """
    tittle = 'Записи соообщества'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related("group")
    post_count = posts.count()
    post_list = Post.objects.filter(group=group)
    paginator = Paginator(post_list, settings.MAX)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'tittle': tittle,
        'group': group,
        'post_count': post_count,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request: HttpRequest, username: str) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон profile.html.
    """
    title = f'Профайл пользователя {username}'
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related("author")
    post_count = posts.count()
    post_list = Post.objects.filter(author=author)
    paginator = Paginator(post_list, settings.MAX)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = False
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user, author=author).exists()
    context = {
        'title': title,
        'author': author,
        'posts': posts,
        'post_count': post_count,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request: HttpRequest, post_id: str) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон post_details.html.
    """
    post = get_object_or_404(Post, pk=post_id)
    title = f'Пост {post.text}'
    author = post.author
    author_posts = author.posts
    post_count = author_posts.count()
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'title': title,
        'author': author,
        'post_count': post_count,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_details.html', context)


@login_required
def post_create(request: HttpRequest) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон post_create.html.
    """
    title = 'Добавить запись'
    groups = Group.objects.all()
    context = {
        'title': title,
        'groups': groups,
    }
    if request.method != 'POST':
        form = PostForm()
        context['form'] = form
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            files=request.FILES or None
        )
        context['form'] = form
    post = form.save(commit=False)
    post.author = request.user
    if request.user != post.author:
        return render(request, 'posts/create_post.html', context)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', context)
    form.save()
    return redirect('posts:profile', username=request.user.username)


@login_required
def post_edit(request: HttpRequest, post_id: str) -> HttpResponse:
    """View-функция обработчик. Принимающая на вход объект
    запроса HttpRequest, возвращающая объект ответа HttpResponse.
    Возвращается Html-шаблон post_create.html.
    """
    title = 'Редактировать запись'
    groups = Group.objects.all()
    post = get_object_or_404(Post, pk=post_id)
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if request.method != 'POST':
        form = PostForm(
            instance=post,
        )
    post.author = request.user
    context = {
        'title': title,
        'groups': groups,
        'post': post,
        'is_edit': is_edit,
        'form': form
    }
    if post.author != request.user:
        return redirect('posts:profile', post.author)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', context)
    form.save()
    return redirect('posts:post_detail', post.pk)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    else:
        return render(request, 'posts/includes/comment.html', {'form': form})
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    author_id = Follow.objects.filter(
        user=request.user).values_list('author', flat=True)
    post_list = Post.objects.filter(author__id__in=author_id)
    paginator = Paginator(post_list, settings.MAX)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.filter(user=user, author=author).delete()
    return redirect('posts:profile', username=username)
