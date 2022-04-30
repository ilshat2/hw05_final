from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django import forms

from posts.models import Post, Group, Follow


User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.author = User.objects.create_user(username='Test_name')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_description',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='test_post',
            group=cls.group,
        )

    def setUp(self):
        self.user = User.objects.create_user(username='ilmarinen')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон. Собираем в словарь
        пары 'reverse(namespace: name): имя_html_шаблона'.
        """
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.author.username}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.pk}): 'posts/post_details.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def assert_post(self, first_object):
        """Дублирующий код проверки постов.
        """
        self.assertEqual(
            first_object.text, self.post.text)
        self.assertEqual(
            first_object.author.username, self.post.author.username)
        self.assertEqual(
            first_object.group.title, self.group.title)
        self.assertEqual(
            first_object.pk, self.post.pk)

    def test_index_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона index.
        """
        response = self.authorized_client.get(
            reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assert_post(first_object)

    def test_profile_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона profile.
        """
        response = (self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.author})))
        first_object = response.context['page_obj'][0]
        self.assert_post(first_object)

    def test_group_list_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона group_list.
        """
        response = (self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})))
        self.assertEqual(response.context.get(
            'group').title, self.group.title)
        self.assertEqual(response.context.get(
            'group').description, self.group.description)
        self.assertEqual(response.context.get(
            'group').slug, self.group.slug)
        self.assertEqual(response.context.get(
            'group').pk, self.group.pk)

    def test_post_detail_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона post_detail.
        """
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})))
        self.assertEqual(response.context.get(
            'post').id, self.post.pk)

    def test_post_create_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона post_create(редактирование).
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        self.assertEqual(response.context.get(
            'post').id, self.post.pk)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_page_show_correct_context(self):
        """Проверяем контекст(context) шаблона post_create(создание).
        """
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.author = User.objects.create_user(username='Test_name')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_description',
            slug='test-slug',
        )
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                author=cls.author,
                text=f'test_post {i}',
                group=cls.group,
            ))
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.user = User.objects.create_user(username='ilmarinen')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Проверяем паджинатор(paginator) первая страница.
        """
        response = self.authorized_client.get(
            reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), settings.MAX)

    def test_second_page_contains_ten_records(self):
        """Проверяем паджинатор(paginator) вторая страница.
        """
        second_page = Post.objects.count() - settings.MAX
        response = self.authorized_client.get(
            reverse('posts:index') + f'?page={second_page}')
        self.assertEqual(len(response.context['page_obj']), second_page)


class CasheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='mirymir')
        cls.post_cashe = Post.objects.create(
            author=cls.author,
            text='Тест кеша',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_cache_index(self):
        """Тестируем кеш шаблона index.
        """
        response = self.authorized_client.get(
            reverse('posts:index')).content
        self.post_cashe.delete()
        response_cashe = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response, response_cashe)
        cache.clear()
        response_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response, response_clear)


class FollowTest(TestCase):
    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(
            username='Bobchinsky', email='bobchinsky@mail.ru', password='pass')
        self.user_following = User.objects.create_user(
            username='Dobchinsky', email='dobchinsky@mail.ru', password='pass')
        self.post = Post.objects.create(
            author=self.user_following,
            text='test_post'
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)

    def test_follow(self):
        self.client_auth_follower.get(reverse('posts:profile_follow', kwargs={
            'username': self.user_following.username}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow(self):
        self.client_auth_follower.get(reverse(
            'posts:profile_follow', kwargs={
                'username': self.user_following.username}))
        self.client_auth_follower.get(reverse(
            'posts:profile_unfollow', kwargs={
                'username': self.user_following.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscription_feed(self):
        Follow.objects.create(
            user=self.user_follower, author=self.user_following)
        response = self.client_auth_follower.get(
            reverse('posts:follow_index'))
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, self.post.text)
        response = self.client_auth_following.get(
            reverse('posts:follow_index'))
        self.assertNotContains(response, self.post.text)
