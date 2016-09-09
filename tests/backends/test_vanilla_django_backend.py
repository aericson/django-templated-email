import base64
from datetime import date
from email.mime.image import MIMEImage

from django.test import TestCase, override_settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.core import mail

from mock import patch
from anymail.message import AnymailMessage

from .utils import TempalteBackendBaseMixin
from templated_email.backends.vanilla_django import TemplateBackend


PLAIN_RESULT = (u'\n  Hi,\n\n  You just signed up for my website, using:\n    '
                u'  username: vintasoftware\n      join date: Aug. 22, 2016\n'
                u'\n  Thanks, you rock!\n')


HTML_RESULT = (u'<p>Hi Foo Bar,</p><p>You just signed up for my website, '
               u'using:<dl><dt>username</dt><dd>vintasoftwar'
               u'e</dd><dt>join date</dt><dd>Aug. 22, 2016</dd></dl>'
               u'</p><p>Thanks, you rock!</p>')

INHERITANCE_RESULT = (u'<h1>Hello Foo Bar,</h1><p>You just signed up for my website, '
                      u'using:<dl><dt>username</dt><dd>Mr. vintasoftwar'
                      u'e</dd><dt>join date</dt><dd>Aug. 22, 2016</dd></dl>'
                      u'</p>')

GENERATED_PLAIN_RESULT = (u'Hi Foo Bar,\n\nYou just signed up for my website, using:'
                          u'\n\nusername\n\n    vintasoftware\njoin date\n'
                          u'\n    Aug. 22, 2016\n\nThanks, you rock!\n\n')

SUBJECT_RESULT = 'My subject for vintasoftware'


PNG_FILE = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00'
            b'\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x01sRGB\x00\xae'
            b'\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00'
            b'\x00\x00\tpHYs\x00\x00\x0e\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00'
            b'\x00\x00\x0cIDAT\x18Wc```\x00\x00\x00\x04\x00\x01\\\xcd\xffi\x00'
            b'\x00\x00\x00IEND\xaeB`\x82')

class TemplateBackendTestCase(TempalteBackendBaseMixin, TestCase):
    template_backend_klass = TemplateBackend

    def setUp(self):
        self.backend = self.template_backend_klass()
        self.context = {'username': 'vintasoftware',
                        'joindate': date(2016, 8, 22),
                        'full_name': 'Foo Bar'}

    def test_inexistent_base_email(self):
        try:
            self.backend._render_email('inexistent_base.email', {})
        except TemplateDoesNotExist as e:
            self.assertEquals(e.args[0], 'foo')

    def test_inexistent_template_email(self):
        try:
            self.backend._render_email('foo', {})
        except TemplateDoesNotExist as e:
            self.assertEquals(e.args[0], 'templated_email/foo.email')

    def test_render_plain_email(self):
        response = self.backend._render_email(
            'plain_template.email', self.context)
        self.assertEquals(len(response.keys()), 2)
        self.assertEquals(PLAIN_RESULT, response['plain'])
        self.assertEquals(SUBJECT_RESULT, response['subject'])

    def test_render_html_email(self):
        response = self.backend._render_email(
            'html_template.email', self.context)
        self.assertEquals(len(response.keys()), 2)
        self.assertHTMLEqual(HTML_RESULT, response['html'])
        self.assertEquals(SUBJECT_RESULT, response['subject'])

    def test_render_mixed_email(self):
        response = self.backend._render_email(
            'mixed_template.email', self.context)
        self.assertEquals(len(response.keys()), 3)
        self.assertHTMLEqual(HTML_RESULT, response['html'])
        self.assertEquals(PLAIN_RESULT, response['plain'])
        self.assertEquals(SUBJECT_RESULT, response['subject'])

    def test_render_inheritance_email(self):
        response = self.backend._render_email(
            'inheritance_template.email', self.context)
        self.assertEquals(len(response.keys()), 3)
        self.assertHTMLEqual(INHERITANCE_RESULT, response['html'])
        self.assertEquals(PLAIN_RESULT, response['plain'])
        self.assertEquals('Another subject for vintasoftware', response['subject'])

    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT, 'subject': SUBJECT_RESULT}
    )
    def test_get_email_message(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, EmailMessage))
        self.assertEquals(message.body, PLAIN_RESULT)
        self.assertEquals(message.subject, SUBJECT_RESULT)
        self.assertEquals(message.to, ['to@example.com'])
        self.assertEquals(message.cc, ['cc@example.com'])
        self.assertEquals(message.bcc, ['bcc@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')

    @override_settings(TEMPLATED_EMAIL_EMAIL_MESSAGE_CLASS=
                       'anymail.message.AnymailMessage')
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT, 'subject': SUBJECT_RESULT}
    )
    def test_custom_emailmessage_klass(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, AnymailMessage))

    @override_settings(TEMPLATED_EMAIL_DJANGO_SUBJECTS={'foo.email':
                                                        'foo\r\n'})
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT}
    )
    def test_get_email_message_without_subject(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, EmailMessage))
        self.assertEquals(message.body, PLAIN_RESULT)
        self.assertEquals(message.subject, 'foo')
        self.assertEquals(message.to, ['to@example.com'])
        self.assertEquals(message.cc, ['cc@example.com'])
        self.assertEquals(message.bcc, ['bcc@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')

    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'html': HTML_RESULT, 'subject': SUBJECT_RESULT}
    )
    def test_get_email_message_genrated_plain_text(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, EmailMultiAlternatives))
        self.assertHTMLEqual(message.alternatives[0][0], HTML_RESULT)
        self.assertEquals(message.alternatives[0][1], 'text/html')
        self.assertEquals(message.body, GENERATED_PLAIN_RESULT)
        self.assertEquals(message.subject, SUBJECT_RESULT)
        self.assertEquals(message.to, ['to@example.com'])
        self.assertEquals(message.cc, ['cc@example.com'])
        self.assertEquals(message.bcc, ['bcc@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')

    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'html': HTML_RESULT, 'plain': PLAIN_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_get_email_message_with_plain_and_html(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, EmailMultiAlternatives))
        self.assertHTMLEqual(message.alternatives[0][0], HTML_RESULT)
        self.assertEquals(message.alternatives[0][1], 'text/html')
        self.assertEquals(message.body, PLAIN_RESULT)
        self.assertEquals(message.subject, SUBJECT_RESULT)
        self.assertEquals(message.to, ['to@example.com'])
        self.assertEquals(message.cc, ['cc@example.com'])
        self.assertEquals(message.bcc, ['bcc@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')


    @override_settings(TEMPLATED_EMAIL_EMAIL_MULTIALTERNATIVES_CLASS=
                       'anymail.message.AnymailMessage')
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'html': HTML_RESULT, 'plain': PLAIN_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_custom_emailmessage_klass_multipart(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, AnymailMessage))

    @override_settings(TEMPLATED_EMAIL_AUTO_PLAIN=False)
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'html': HTML_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_get_email_message_html_only(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'])
        self.assertTrue(isinstance(message, EmailMessage))
        self.assertHTMLEqual(message.body, HTML_RESULT)
        self.assertEquals(message.content_subtype, 'html')
        self.assertEquals(message.subject, SUBJECT_RESULT)
        self.assertEquals(message.to, ['to@example.com'])
        self.assertEquals(message.cc, ['cc@example.com'])
        self.assertEquals(message.bcc, ['bcc@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')

    # this can be too slow, mock it for speed.
    # See: https://code.djangoproject.com/ticket/24380
    @patch('django.core.mail.utils.socket.getfqdn', return_value='vinta.local')
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'html': HTML_RESULT, 'plain': PLAIN_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_send(self, render_mock, getfqdn_mock):
        ret = self.backend.send('mixed_template', 'from@example.com',
                                ['to@example.com', 'to2@example.com'], {},
                                headers={'Message-Id': 'a_message_id'})
        self.assertEquals(ret, 'a_message_id')
        self.assertEquals(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEquals(ret, message.extra_headers['Message-Id'])
        self.assertTrue(isinstance(message, EmailMultiAlternatives))
        self.assertHTMLEqual(message.alternatives[0][0], HTML_RESULT)
        self.assertEquals(message.alternatives[0][1], 'text/html')
        self.assertEquals(message.body, PLAIN_RESULT)
        self.assertEquals(message.subject, SUBJECT_RESULT)
        self.assertEquals(message.to, ['to@example.com', 'to2@example.com'])
        self.assertEquals(message.from_email, 'from@example.com')

    @patch.object(
        template_backend_klass, 'get_email_message'
    )
    @patch(
        'templated_email.backends.vanilla_django.get_connection'
    )
    def test_all_arguments_passed_forward_from_send(
            self, get_connection_mock, get_email_message_mock):
        kwargs = {
            'template_name': 'foo',
            'from_email': 'from@example.com',
            'recipient_list': ['to@example.com'],
            'context': {'foo': 'bar'},
            'cc': ['cc@example.com'],
            'bcc': ['bcc@example.com'],
            'fail_silently': True,
            'headers': {'Message-Id': 'a_message_id'},
            'template_prefix': 'prefix',
            'template_suffix': 'suffix',
            'template_dir': 'tempdir',
            'file_extension': 'ext',
            'auth_user': 'vintasoftware',
            'auth_password': 'password',
        }

        send_mock = get_email_message_mock.return_value.send
        self.backend.send(**kwargs)
        get_connection_mock.assert_called_with(
            username=kwargs['auth_user'],
            password=kwargs['auth_password'],
            fail_silently=kwargs['fail_silently']
        )
        get_email_message_mock.assert_called_with(
            kwargs['template_name'],
            kwargs['context'],
            from_email=kwargs['from_email'],
            to=kwargs['recipient_list'],
            cc=kwargs['cc'],
            bcc=kwargs['bcc'],
            headers=kwargs['headers'],
            template_prefix=kwargs['template_prefix'],
            template_suffix=kwargs['template_suffix'],
            template_dir=kwargs['template_dir'],
            file_extension=kwargs['file_extension'],
            attachments=None,
        )
        send_mock.assert_called_with(
            kwargs['fail_silently']
        )

    # this can be too slow, mock it for speed.
    # See: https://code.djangoproject.com/ticket/24380
    @patch('django.core.mail.utils.socket.getfqdn', return_value='vinta.local')
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_send_attachment_mime_base(self, render_mock, getfqdn_mock):
        self.backend.send('plain_template', 'from@example.com',
                          ['to@example.com', 'to2@example.com'], {},
                          attachments=[MIMEImage(PNG_FILE, 'image/png')])
        attachment = mail.outbox[0].attachments[0]
        self.assertEquals(attachment.get_payload().replace('\n', ''),
                          base64.b64encode(PNG_FILE))

    # this can be too slow, mock it for speed.
    # See: https://code.djangoproject.com/ticket/24380
    @patch('django.core.mail.utils.socket.getfqdn', return_value='vinta.local')
    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT,
                      'subject': SUBJECT_RESULT}
    )
    def test_send_attachment_tripple(self, render_mock, getfqdn_mock):
        self.backend.send('plain_template', 'from@example.com',
                          ['to@example.com', 'to2@example.com'], {},
                          attachments=[('black_pixel.png', PNG_FILE, 'image/png')])
        attachment = mail.outbox[0].attachments[0]
        self.assertEquals(('black_pixel.png', PNG_FILE, 'image/png'),
                          attachment)

    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT, 'subject': SUBJECT_RESULT}
    )
    def test_get_email_message_attachment_mime_base(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'],
            attachments=[MIMEImage(PNG_FILE, 'image/png')])
        attachment = message.attachments[0]
        self.assertEquals(attachment.get_payload().replace('\n', ''),
                          base64.b64encode(PNG_FILE))

    @patch.object(
        template_backend_klass, '_render_email',
        return_value={'plain': PLAIN_RESULT, 'subject': SUBJECT_RESULT}
    )
    def test_get_email_message_attachment_tripple(self, mock):
        message = self.backend.get_email_message(
            'foo.email', {},
            from_email='from@example.com', cc=['cc@example.com'],
            bcc=['bcc@example.com'], to=['to@example.com'],
            attachments=[('black_pixel.png', PNG_FILE, 'image/png')])
        attachment = message.attachments[0]
        self.assertEquals(('black_pixel.png', PNG_FILE, 'image/png'),
                          attachment)
