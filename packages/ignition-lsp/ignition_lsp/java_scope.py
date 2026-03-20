"""Java scope tracking for Jython import detection and completion context."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from pygls.workspace import TextDocument

from .java_loader import JavaAPILoader, JavaClass

logger = logging.getLogger(__name__)

# Regex patterns for Jython/Python import statements
# "from java.net import URL"
# "from java.net import URL, HttpURLConnection"
# "from java.net import URL as MyURL"
_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+([\w.]+)\s+import\s+(.+)$"
)
# "import java.net.URL"
# "import java.net.URL as URL"
_IMPORT_RE = re.compile(
    r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?\s*$"
)


class JavaContextType(Enum):
    """Types of Java-related completion contexts."""

    IMPORT_PACKAGE = "import_package"  # from java.|  -> offer sub-packages
    IMPORT_CLASS = "import_class"  # from java.net import |  -> offer classes
    CLASS_MEMBER = "class_member"  # url.|  where url type is known -> offer methods
    CONSTRUCTOR = "constructor"  # URL(|  -> offer constructor params
    STATIC_MEMBER = "static_member"  # Integer.|  used as class name -> offer static methods/fields


@dataclass
class JavaContext:
    """Describes the Java completion context at cursor."""

    type: JavaContextType
    # For IMPORT_PACKAGE: the package prefix (e.g., "java" or "java.net")
    # For IMPORT_CLASS: the package name (e.g., "java.net")
    # For CLASS_MEMBER/STATIC_MEMBER: the JavaClass
    # For CONSTRUCTOR: the JavaClass
    package: str = ""
    java_class: Optional[JavaClass] = None
    partial: str = ""  # Partial text typed after the trigger


def scan_imports(document: TextDocument, java_loader: JavaAPILoader) -> Dict[str, JavaClass]:
    """Scan document for Java import statements.

    Returns a mapping of local name -> JavaClass for all recognized imports.
    Example: {"URL": JavaClass("java.net.URL"), "JException": JavaClass("java.lang.Exception")}
    """
    result: Dict[str, JavaClass] = {}

    for line in document.lines:
        line = line.rstrip("\n\r")

        # Skip comments
        if line.lstrip().startswith("#"):
            continue

        # Try "from pkg import cls1, cls2, cls3 as alias"
        m = _FROM_IMPORT_RE.match(line)
        if m:
            package = m.group(1)
            imports_str = m.group(2)
            _parse_from_import(package, imports_str, java_loader, result)
            continue

        # Try "import pkg.ClassName" or "import pkg.ClassName as Alias"
        m = _IMPORT_RE.match(line)
        if m:
            full_path = m.group(1)
            alias = m.group(2)
            _parse_direct_import(full_path, alias, java_loader, result)
            continue

    return result


def _parse_from_import(
    package: str,
    imports_str: str,
    java_loader: JavaAPILoader,
    result: Dict[str, JavaClass],
) -> None:
    """Parse 'from pkg import A, B, C as D' into result dict."""
    for item in imports_str.split(","):
        item = item.strip()
        if not item:
            continue

        # Handle "ClassName as Alias"
        as_match = re.match(r"(\w+)\s+as\s+(\w+)", item)
        if as_match:
            class_name = as_match.group(1)
            alias = as_match.group(2)
        else:
            # Just "ClassName"  (strip trailing comments/whitespace)
            class_name = item.split()[0] if item.split() else item
            alias = class_name

        full_name = f"{package}.{class_name}"
        cls = java_loader.get_class(full_name)
        if cls:
            result[alias] = cls


def _parse_direct_import(
    full_path: str,
    alias: Optional[str],
    java_loader: JavaAPILoader,
    result: Dict[str, JavaClass],
) -> None:
    """Parse 'import java.net.URL' or 'import java.net.URL as U' into result dict."""
    cls = java_loader.get_class(full_path)
    if cls:
        local_name = alias if alias else cls.name
        result[local_name] = cls


def detect_java_context(
    document: TextDocument,
    position,
    java_loader: JavaAPILoader,
) -> Optional[JavaContext]:
    """Determine if cursor is in a Java-related completion context.

    Returns JavaContext describing the context, or None if not Java-related.
    """
    line = document.lines[position.line]
    text_before = line[:position.character]

    # Check for import statement contexts first
    ctx = _detect_import_context(text_before, java_loader)
    if ctx:
        return ctx

    # Check for class member / constructor contexts (imported names)
    ctx = _detect_member_context(text_before, document, java_loader)
    if ctx:
        return ctx

    # Check for inline fully-qualified Java references (e.g., java.lang.Thread.)
    ctx = _detect_inline_qualified_context(text_before, java_loader)
    if ctx:
        return ctx

    return None


def _detect_import_context(
    text_before: str, java_loader: JavaAPILoader
) -> Optional[JavaContext]:
    """Detect import-related completion contexts.

    Handles:
        "from java."           -> IMPORT_PACKAGE (offer sub-packages under "java")
        "from java.net."       -> IMPORT_PACKAGE (offer sub-packages under "java.net")
        "from java.net import " -> IMPORT_CLASS (offer classes in java.net)
        "from java.net import U" -> IMPORT_CLASS with partial "U"
        "from java.net import URL, " -> IMPORT_CLASS (offer more classes)
    """
    stripped = text_before.strip()

    # "from java.net import URL, H" or "from java.net import "
    m = re.match(r"from\s+([\w.]+)\s+import\s*(.*)", stripped)
    if m:
        package = m.group(1)
        after_import = m.group(2)

        # Check if this package has classes in our database
        if java_loader.get_package_classes(package):
            # Determine partial: last item after comma
            parts = after_import.split(",")
            partial = parts[-1].strip() if parts else ""
            return JavaContext(
                type=JavaContextType.IMPORT_CLASS,
                package=package,
                partial=partial,
            )
        return None

    # "from java." or "from java.net."
    m = re.match(r"from\s+([\w.]+)\.\s*$", stripped)
    if m:
        prefix = m.group(1)
        return JavaContext(
            type=JavaContextType.IMPORT_PACKAGE,
            package=prefix,
            partial="",
        )

    # "from java.n" (partial package segment)
    m = re.match(r"from\s+([\w.]+)$", stripped)
    if m:
        typed = m.group(1)
        # Check if it ends with a partial segment
        if "." in typed:
            prefix = typed.rsplit(".", 1)[0]
            partial = typed.rsplit(".", 1)[1]
            # Only trigger if prefix is a known package or parent
            subs = java_loader.get_sub_packages(prefix)
            if subs:
                return JavaContext(
                    type=JavaContextType.IMPORT_PACKAGE,
                    package=prefix,
                    partial=partial,
                )

    return None


def _detect_member_context(
    text_before: str, document: TextDocument, java_loader: JavaAPILoader
) -> Optional[JavaContext]:
    """Detect class member or constructor completion contexts.

    Handles:
        "url."         where url's type is URL (imported) -> CLASS_MEMBER
        "URL."         where URL is an imported class     -> STATIC_MEMBER
        "URL("         constructor call                   -> CONSTRUCTOR
        "Integer."     static access                      -> STATIC_MEMBER
    """
    # Scan imports to know what's in scope
    imported = scan_imports(document, java_loader)
    if not imported:
        return None

    stripped = text_before.rstrip()

    # Check for "ClassName(" -> CONSTRUCTOR
    m = re.search(r"(\w+)\(\s*$", stripped)
    if m:
        name = m.group(1)
        if name in imported:
            return JavaContext(
                type=JavaContextType.CONSTRUCTOR,
                java_class=imported[name],
            )

    # Check for "name." -> CLASS_MEMBER or STATIC_MEMBER
    m = re.search(r"(\w+)\.\s*(\w*)$", stripped)
    if m:
        name = m.group(1)
        partial = m.group(2)
        if name in imported:
            cls = imported[name]
            # If the name starts with uppercase, likely static access (e.g., Integer.parseInt)
            # If lowercase, likely instance method access (e.g., url.openConnection)
            # But both should work — we just return different context types for detail display
            if name[0].isupper():
                return JavaContext(
                    type=JavaContextType.STATIC_MEMBER,
                    java_class=cls,
                    partial=partial,
                )
            else:
                return JavaContext(
                    type=JavaContextType.CLASS_MEMBER,
                    java_class=cls,
                    partial=partial,
                )

    return None


def _detect_inline_qualified_context(
    text_before: str, java_loader: JavaAPILoader
) -> Optional[JavaContext]:
    """Detect fully-qualified Java references used inline in code.

    Jython allows using Java classes without imports:
        java.lang.Thread.sleep(1000)
        com.inductiveautomation.ignition.common.LoggerEx.getLogger("name")

    Handles:
        "java."                -> IMPORT_PACKAGE (sub-packages: lang, net, util, ...)
        "java.lang."           -> IMPORT_CLASS (classes: String, Integer, ...)
        "java.lang.Thread."    -> STATIC_MEMBER (methods on Thread)
        "java.lang.Th"        -> IMPORT_CLASS with partial "Th"
        "com.inductiveautomation." -> IMPORT_PACKAGE
    """
    # Extract the trailing qualified identifier (e.g., "java.lang.Thread." or "java.lang.")
    m = re.search(r"([\w.]+)\.\s*(\w*)$", text_before)
    if not m:
        return None

    qualified = m.group(1)  # e.g., "java.lang.Thread" or "java.lang" or "java"
    partial = m.group(2)    # e.g., "" or "Th" or "sleep"

    # Only trigger for Java-like prefixes to avoid false positives
    if not _looks_like_java_prefix(qualified):
        return None

    # Check if qualified is an exact class name -> offer static members
    cls = java_loader.get_class(qualified)
    if cls:
        return JavaContext(
            type=JavaContextType.STATIC_MEMBER,
            java_class=cls,
            partial=partial,
        )

    # Check if qualified is a known package -> offer classes in that package
    if java_loader.get_package_classes(qualified):
        return JavaContext(
            type=JavaContextType.IMPORT_CLASS,
            package=qualified,
            partial=partial,
        )

    # Check if qualified is a package prefix -> offer sub-packages
    subs = java_loader.get_sub_packages(qualified)
    if subs:
        return JavaContext(
            type=JavaContextType.IMPORT_PACKAGE,
            package=qualified,
            partial=partial,
        )

    return None


def _looks_like_java_prefix(qualified: str) -> bool:
    """Heuristic: does this look like a Java/Ignition qualified name?

    Avoids false positives on things like 'self.value' or 'system.tag'.
    """
    return qualified.startswith((
        "java.",
        "javax.",
        "com.inductiveautomation.",
    )) or qualified in ("java", "javax", "com", "com.inductiveautomation")
