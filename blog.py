from fasthtml.common import *
from datetime import datetime


db = database('data/blog.db')
articles,users = db.t.articles,db.t.users
if articles not in db.t:
    # You can pass a dict, or kwargs, to most MiniDataAPI methods.
    users.create(dict(name=str, pwd=str), pk='name')
    articles.create(title=str, slug=str, name=str, content=str, pub_date=datetime, published=bool, pk='slug')
# Although you can just use dicts, it can be helpful to have types for your DB objects.
# The `dataclass` method creates that type, and stores it in the object, so it will use it for any returned items.
Article,User = articles.dataclass(),users.dataclass()

login_redir = RedirectResponse('/login', status_code=303)

def before(req, sess):
    auth = req.scope['auth'] = sess.get('auth', None)
    if not auth: return login_redir
    articles.xtra(name=auth)

bware = Beforeware(before, skip=[r'/', r'/[a-z\-]+', r'/static/.*', r'.*\.css', '/login'])

app,rt = fast_app(before=bware)

@rt('/')
def get():

    return Titled('Welcome to my blog', 
        P(A(link=uri('article_create'))("Write an article")),
        *[P(A(href=x.slug)(x.title)) for x in articles()]
    )

# For instance, this function handles GET requests to the `/login` path.
@rt("/login")
def get():
    frm = Form(
        # Tags with a `name` attr will have `name` auto-set to the same as `id` if not provided
        Input(id='name', placeholder='Name'),
        Input(id='pwd', type='password', placeholder='Password'),
        Button('login'),
        action='/login', method='post')
    return Titled("Login", frm)

@dataclass
class Login: name:str; pwd:str

@rt("/login")
def post(login:Login, sess):
    if not login.name or not login.pwd: return login_redir
    try: u = users[login.name]
    except NotFoundError: u = users.insert(login)
    if not compare_digest(u.pwd.encode("utf-8"), login.pwd.encode("utf-8")): return login_redir
    sess['auth'] = u.name
    return RedirectResponse('/', status_code=303)

@app.get("/logout")
def logout(sess):
    if 'auth' in sess: del sess['auth']
    return login_redir

@rt('/~article/create', name='article_create')
def get():
    return Titled('Write an article', Form(action='/~article-creation', method="post")(
        Label("Title", For="title")(Input(type="text", id="title", name="title", required=True, autofocus=True)),
        Label("Pub Date", For="pub_date")(Input(type="datetime-local", id="pub_date", name="pub_date")),
        Label("Content", For="content")(Textarea(id="content", name="content", rows=10, required=True)),
        Label("Published", For="published")(Input(type="checkbox", id="published", name="published")),
        Button("Submit")
        ))

@rt('/~article-creation')
def post(article:Article):
    article.slug = article.title.lower().replace(' ', '-')
    print(article)
    articles.insert(article)
    return RedirectResponse('/', status_code=303)

@rt('/{slug:str}')
def get(slug:str):
    a = articles[slug]
    return Titled(a.title, Section(cls='marked')(a.content))

serve()