import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';

let isRefreshing = false;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('access_token');

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error) => {
      if (
        error.status === 401 &&
        !req.url.includes('/auth/refresh/') &&
        !req.url.includes('/auth/login/') &&
        !isRefreshing
      ) {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          isRefreshing = true;
          const http = inject(HttpClient);
          return http
            .post<{ access: string }>(
              `${environment.apiUrl}/auth/refresh/`,
              { refresh: refreshToken }
            )
            .pipe(
              switchMap((tokens) => {
                isRefreshing = false;
                localStorage.setItem('access_token', tokens.access);
                const retryReq = req.clone({
                  setHeaders: { Authorization: `Bearer ${tokens.access}` },
                });
                return next(retryReq);
              }),
              catchError((refreshError) => {
                isRefreshing = false;
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                return throwError(() => refreshError);
              })
            );
        }
      }
      return throwError(() => error);
    })
  );
};
