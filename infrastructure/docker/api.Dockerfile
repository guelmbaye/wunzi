FROM php:8.3-cli-alpine

RUN apk add --no-cache git unzip icu-dev postgresql-dev libzip-dev oniguruma-dev linux-headers $PHPIZE_DEPS \
 && docker-php-ext-install pdo pdo_pgsql intl zip bcmath opcache \
 && pecl install redis && docker-php-ext-enable redis \
 && apk del $PHPIZE_DEPS

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html
COPY apps/api/composer.json ./composer.json
RUN composer install --no-interaction --no-scripts --prefer-dist || true

COPY apps/api /var/www/html
EXPOSE 8000
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]
