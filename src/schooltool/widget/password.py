from zope.app.form.browser import PasswordWidget
from zope.app.form.browser.widget import renderElement
from zope.app.form.interfaces import ConversionError
from zope.i18n import translate

from schooltool import SchoolToolMessage as _

class PasswordConfirmationWidget(PasswordWidget):
    """Password Widget that uses two fields to confirm user input.
    """

    default = ''
    type = 'password'
    displayWidth = 15
    
    def __call__(self):
        password_tag = renderElement(
                self.tag,
                type=self.type,
                name=self.name,
                id=self.name,
                value=self.default,
                cssClass=self.cssClass,
                style=self.style,
                size=self.displayWidth,
                extra=self.extra)
        confirm_tag = renderElement(
                self.tag,
                type=self.type,
                name=self.name + '.confirm',
                id=self.name + '.confirm',
                value=self.default,
                cssClass=self.cssClass,
                style=self.style,
                size=self.displayWidth,
                extra=self.extra)
        return translate(_(u"${password} Confirm: ${confirm}",
                           mapping={'password': password_tag,
                                    'confirm': confirm_tag}))

    def _toFieldValue(self, input):
        """Check whether the confirmation field value is identical to
        the password value.
        """
        formdata = self.request.form
        if input != formdata[self.name + '.confirm']:
            raise ConversionError(_(u"Supplied passwords are not identical"),
                                  '')
        return super(PasswordConfirmationWidget, self)._toFieldValue(input)

    def hasInput(self):
        """Check whether the field is represented in the form.
        """
        return self.name + ".confirm" in self.request.form or \
          super(PasswordConfirmationWidget, self).hasInput()

    def hidden(self):
        raise NotImplementedError(
            'Cannot get a hidden tag for a password field')
