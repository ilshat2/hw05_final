import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Post, Group, Comment
from posts.forms import PostForm


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Test_name')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test-slug',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='test_post',
            group=cls.group,
            image=uploaded,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='ilmarinen')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post.
        """
        posts = Post.objects.count() + 1
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        form = {
            'text': 'test_text_form',
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form,
            follow=True,
        )
        self.assertEqual(
            Post.objects.count(),
            posts,
        )
        post_object = Post.objects.get(pk=posts)
        self.assertTrue(
            Post.objects.filter(
                pk=posts,
                text=post_object.text,
                image=post_object.image,
            ).exists()
        )
        post_object = str(post_object)
        self.assertEqual(form['text'], post_object)

    def test_image_post(self):
        """Передаем image через контекст(context) в index, profile, group_list.
        """
        all_address = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': 'Test_name'}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        ]
        for address in all_address:
            response = self.authorized_client.get(address)
            post_object = response.context['page_obj'][0]
            self.assertEqual(post_object.image, self.post.image)

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post.
        """
        post = Post.objects.count()
        form = {
            'text': 'test_text_form'
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form,
            follow=True,
        )
        self.assertEqual(
            Post.objects.count(),
            post,
        )
        self.post.refresh_from_db()
        self.assertEqual(
            self.post.text,
            form['text']
        )

    def test_comments(self):
        """Комментировать посты может только авторизованный пользователь.
        """
        form = {
            'post': self.post,
            'author': self.author,
            'text': 'test_comment',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form,
            follow=True,
        )
        comment = Comment.objects.first()
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.text, form['text'])
        self.assertEqual(comment.post, self.post)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
