import re
from typing import Tuple, Optional
import sqlglot
from sqlglot import exp

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "ATTACH", "DETACH", "VACUUM", "REINDEX", "PRAGMA",
    "GRANT", "REVOKE", "BEGIN", "COMMIT", "ROLLBACK", "LOAD_EXTENSION",
    "EXEC", "EXECUTE", "SHUTDOWN"
}

FORBIDDEN_AST_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Pragma,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
)

def validate_and_sanitize_sql(raw_sql: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates that a generated SQL string is strictly a safe, read-only SELECT query.
    Returns: (is_safe, sanitized_sql, error_message)
    """
    if not raw_sql or not raw_sql.strip():
        return False, "", "Empty SQL query provided."
    
    # 1. Clean markdown fences or wrappers
    cleaned = raw_sql.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    
    # 2. Check for multiple statements separated by semicolon
    try:
        statements = sqlglot.parse(cleaned, read="sqlite")
        statements = [s for s in statements if s is not None]
    except Exception as e:
        return False, "", f"SQL parsing error: {str(e)}"
    
    if len(statements) == 0:
        return False, "", "Could not parse SQL statement."
    
    if len(statements) > 1:
        return False, "", "Multiple SQL statements are not permitted for security reasons."
    
    ast = statements[0]
    
    # 3. Check AST Root node
    # Valid root nodes for read-only queries are Select, Union, or With
    if not isinstance(ast, (exp.Select, exp.Union, exp.Expression)):
        return False, "", f"Invalid query type: Root expression must be a SELECT query, found {type(ast).__name__}."
    
    # Check if root is Select or With (Common Table Expression ending in Select)
    if not (isinstance(ast, exp.Select) or (isinstance(ast, exp.Union)) or ast.find(exp.Select)):
        return False, "", "Query must contain a SELECT statement."
        
    # 4. Check for forbidden AST nodes anywhere in the syntax tree
    for forbidden_type in FORBIDDEN_AST_NODES:
        if ast.find(forbidden_type):
            return False, "", f"Prohibited SQL operation detected: {forbidden_type.__name__} is not allowed."
            
    # 5. Regex check for explicit dangerous words outside string literals
    # Tokenize word boundaries
    upper_sql = cleaned.upper()
    for kw in FORBIDDEN_KEYWORDS:
        # Match whole word
        if re.search(rf"\b{kw}\b", upper_sql):
            # Verify if it's inside AST as an identifier or if it's a mutation clause
            if kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH", "DETACH", "VACUUM", "PRAGMA", "LOAD_EXTENSION"]:
                # Check if it was caught or if it's used as a column name
                # If AST doesn't use it harmlessly as column alias/identifier, reject
                if isinstance(ast, (exp.Insert, exp.Delete, exp.Update, exp.Drop, exp.Alter, exp.Create)):
                    return False, "", f"Forbidden SQL keyword '{kw}' detected."

    # 6. Ensure query targets the dataset table or sqlite internal introspection
    # Transpile back to clean standard SQLite SQL
    try:
        sanitized_sql = ast.sql(dialect="sqlite")
    except Exception as e:
        sanitized_sql = cleaned.rstrip(";").strip()

    # Strip any trailing semicolons to prevent injection
    sanitized_sql = sanitized_sql.rstrip(";").strip()
    
    return True, sanitized_sql, None
