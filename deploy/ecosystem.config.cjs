module.exports = {
  apps: [
    {
      name: "pt-incendios-api",
      cwd: "/var/www/pt_incendios_ml/backend/api-rest",
      script: "src/app.js",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "512M",
      env_production: {
        NODE_ENV: "production",
        HOST: "127.0.0.1",
        PORT: "3000",
      },
    },
  ],
};
