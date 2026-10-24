"""``TemplateToken``: one piece of a dynamic attribute's template (EWR-03, DD-026).

Each piece has the template's text as ``value`` and is evaluated on the entity being written by ``eval``.
"""

from aurelius_atlas_typesystem.attribute_token import AttributeToken
from aurelius_atlas_typesystem.constant_token import ConstantToken
from aurelius_atlas_typesystem.dependent_token import DependentToken

type TemplateToken = ConstantToken | AttributeToken | DependentToken
"""A piece of a ``dynAttribute:`` template."""
