# Despliegue EC2

Esta carpeta contiene la configuración base para desplegar la aplicación en una instancia EC2 con Ubuntu, Nginx, PM2, MongoDB Atlas y Cloudflare R2.

## Estructura esperada en la instancia

```text
/var/www/pt_incendios_ml
├── backend/api-rest
├── frontend
└── deploy
```

## Backend

1. Crear `backend/api-rest/.env` a partir de `.env.example`.
2. Definir `NODE_ENV=production`.
3. Configurar Atlas, R2 y `CORS_ORIGINS=https://<dominio>`.
4. Instalar dependencias con `npm ci`.
5. Arrancar con PM2:

```bash
pm2 start deploy/ecosystem.config.cjs --env production
pm2 save
pm2 startup
```

El backend queda enlazado a `127.0.0.1:3000` y no debe exponerse directamente en el Security Group.

## Frontend

```bash
cd frontend
npm ci
npm run build
```

En producción se recomienda no definir `VITE_API_URL`; el frontend utilizará el mismo origen y Nginx enviará `/api/*` al backend.

## Nginx y HTTPS

El certificado todavía no existe durante el primer arranque, por lo que el proceso se divide en dos etapas.

### 1. Bootstrap HTTP para emitir el certificado

1. Reemplazar `__DOMAIN__` en `deploy/nginx/pt-incendios.bootstrap.conf.example` por el dominio definitivo.
2. Copiarlo a `/etc/nginx/sites-available/pt-incendios`.
3. Crear el enlace en `/etc/nginx/sites-enabled/pt-incendios`.
4. Validar y recargar Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

5. Instalar Certbot y emitir el certificado:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <dominio>
```

### 2. Configuración HTTPS definitiva

Después de que Let's Encrypt haya creado los archivos del certificado:

1. Reemplazar `__DOMAIN__` en `deploy/nginx/pt-incendios.conf.example`.
2. Sustituir la configuración activa por esa versión.
3. Validar y recargar Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

La configuración final redirige HTTP a HTTPS, sirve `frontend/dist` y actúa como reverse proxy para `/api/` hacia `127.0.0.1:3000`.

## Verificación

Una vez levantado el entorno:

```bash
curl https://<dominio>/api/health
```

El endpoint debe responder `status: "ok"` con MongoDB conectado y R2 configurado.
