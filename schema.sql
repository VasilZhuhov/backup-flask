drop table if exists books;
create table books (
  id integer primary key autoincrement,
  owner text not null,
  title text not null
);

drop table if exists users;
create table users (
  id integer primary key autoincrement,
  name text not null,
  password text not null
);

