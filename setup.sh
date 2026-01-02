mkdir -p ~/.streamlit/

echo "\
[server]\n\
port = 8000\n\
address = \"0.0.0.0\"\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml