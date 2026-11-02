import itertools

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from bookmarks.models import BookmarkSearch
from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
    BookmarkListTestMixin,
    TagCloudTestMixin,
)

class BookmarkIndexViewTagListingTestCase(
    TestCase, BookmarkFactoryMixin, BookmarkListTestMixin, TagCloudTestMixin
):
    """
    Quadro 22 (partições):
      TV: visibilidade   -> visible / archived
      TA: autor          -> self / other user
      TL: leitura        -> read / unread
      TC: conjunto       -> bundle existente (news / study)
    """

    def setUp(self) -> None:
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)
        self.other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )

    def _setup_case(self, archived, own, unread, bundle_term, tag_name):
        """Cria um favorito com uma tag única e retorna a tag."""
        tag = self.setup_tag(name=tag_name)
        self.setup_bookmark(
            title=f"{bundle_term or 'plain'} {tag_name}",
            tags=[tag],
            is_archived=archived,
            unread=unread,
            user=self.user if own else self.other_user,
        )
        return tag

    def _get_index(self, bundle=None):
        url = reverse("linkding:bookmarks.index")
        if bundle is not None:
            url += f"?bundle={bundle.id}"
        return self.client.get(url)

    def test_case_01_visible_self_read_news_lists_tag(self):

        bundle = self.setup_bundle(name="News", search="news")
        tag = self._setup_case(False, True, False, "news", "tagcase01")

        response = self._get_index(bundle)

        self.assertVisibleTags(response, [tag])

    def test_case_02_archived_other_user_unread_no_bundle_hides_tag(self):

        tag = self._setup_case(True, False, True, None, "tagcase02")

        response = self._get_index()

        self.assertInvisibleTags(response, [tag])

    def test_case_03_visible_self_read_study_lists_tag(self):

        bundle = self.setup_bundle(name="Study", search="study")
        tag = self._setup_case(False, True, False, "study", "tagcase03")

        response = self._get_index(bundle)

        self.assertVisibleTags(response, [tag])

    def test_case_04_archived_other_user_unread_no_bundle_hides_tag(self):

        tags = [
            self._setup_case(True, False, True, None, f"tagcase04{i}")
            for i in range(3)
        ]

        response = self._get_index()

        self.assertInvisibleTags(response, tags)

    def test_case_05_visible_invalid_author_unread_null_bundle(self):

        tag = self._setup_case(False, False, True, None, "tagcase05")

        response = self._get_index()

        self.assertEqual(response.status_code, 200)
        self.assertInvisibleTags(response, [tag])

    def test_case_06_archived_read_null_bundle(self):

        tag = self._setup_case(True, True, False, None, "tagcase06")

        response = self._get_index()

        self.assertEqual(response.status_code, 200)
        self.assertInvisibleTags(response, [tag])

    def test_case_07_null_visibility_other_user_read(self):

        tag = self._setup_case(False, False, False, None, "tagcase07")

        response = self._get_index()

        self.assertEqual(response.status_code, 200)
        self.assertInvisibleTags(response, [tag])

    def test_case_08_nonexistent_bundle_id(self):

        tag = self._setup_case(False, True, True, None, "tagcase08")

        response = self.client.get(
            reverse("linkding:bookmarks.index") + "?bundle=999999"
        )

        self.assertIn(response.status_code, (200, 404))
        if response.status_code == 200:
            self.assertVisibleTags(response, [tag])

    def test_should_list_tags_for_read_and_unread_bookmarks_by_default(self):
        read_tag = self._setup_case(False, True, False, None, "tagread")
        unread_tag = self._setup_case(False, True, True, None, "tagunread")

        response = self._get_index()

        self.assertVisibleTags(response, [read_tag, unread_tag])

    def test_should_list_only_unread_tags_with_unread_filter(self):
        read_tag = self._setup_case(False, True, False, None, "tagread")
        unread_tag = self._setup_case(False, True, True, None, "tagunread")

        response = self.client.get(
            reverse("linkding:bookmarks.index")
            + f"?unread={BookmarkSearch.FILTER_UNREAD_YES}"
        )

        self.assertVisibleTags(response, [unread_tag])
        self.assertInvisibleTags(response, [read_tag])
