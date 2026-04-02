# Server Setup Guide: MT5 Terminal

This guide outlines the steps to set up the MetaTrader 5 terminal and its API on a Linux server using Docker and Nginx.

## Prerequisites

- A Linux server (Ubuntu 22.04+ recommended).
- Docker and Docker Compose installed.
- A domain name with A records pointing to your server's IP.

## 1. Clone the Repository

```bash
git clone https://github.com/nodalytics/metatrader-terminal.git
cd metatrader-terminal
```

## 2. Environment Configuration

Create a `.env` file from the example and fill in your MT5 credentials:

```bash
cp MT5/.env.example .env
```

At minimum, set the following for auto-login:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo
```

When all three are set, the container will automatically log in to your MT5 account on startup via VNC automation and verify the connection before starting the API.

## 3. Deployment

### With Docker Compose

```bash
docker compose -f MT5/docker-compose.yml --env-file .env up -d
```

### With Docker (standalone)

```bash
docker run -d \
  --name mt5-terminal \
  -p 6901:6901 \
  -p 8000:8000 \
  -e MT5_LOGIN=12345678 \
  -e MT5_PASSWORD=your_password \
  -e MT5_SERVER=YourBroker-Demo \
  -e VNC_PASSWORD=password \
  ghcr.io/nodalytics/mt5-terminal:latest
```

This will start the MT5 terminal (VNC), auto-login to your account, and launch the FastAPI server.

## 4. Nginx Configuration

1.  **Copy snippets**:
    ```bash
    sudo cp nginx/snippets/proxy_params.conf /etc/nginx/snippets/
    ```
2.  **Copy site config**:
    ```bash
    sudo cp nginx/sites-available/mt5 /etc/nginx/sites-available/
    ```
3.  **Edit site config**:
    Update the `server_name` in `/etc/nginx/sites-available/mt5` with your actual subdomains.
4.  **Enable the site**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/mt5 /etc/nginx/sites-enabled/
    ```
5.  **Test and Reload**:
    ```bash
    sudo nginx -t
    sudo systemctl reload nginx
    ```

## 5. SSL with Certbot (Optional but Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d vnc.yourdomain.com -d api.yourdomain.com
```

## 6. Accessing the Services

- **MT5 VNC**: `https://vnc.yourdomain.com`
- **MT5 API**: `https://api.yourdomain.com`
