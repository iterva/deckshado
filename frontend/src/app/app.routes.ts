import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./pages/home/home.component').then(m => m.HomeComponent) },
  { path: 'login', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'register', loadComponent: () => import('./pages/register/register.component').then(m => m.RegisterComponent) },
  { path: 'cards', loadComponent: () => import('./pages/card-list/card-list.component').then(m => m.CardListComponent) },
  { path: 'decks', loadComponent: () => import('./pages/deck-list/deck-list.component').then(m => m.DeckListComponent) },
  { path: 'decks/:id', loadComponent: () => import('./pages/deck-view/deck-view.component').then(m => m.DeckViewComponent) },
  { path: 'builder', loadComponent: () => import('./pages/format-select/format-select.component').then(m => m.FormatSelectComponent) },
  { path: 'builder/new/:format', loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent) },
  { path: 'builder/:id', loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent) },
  { path: 'team', loadComponent: () => import('./pages/team/team.component').then(m => m.TeamComponent) },
  { path: '**', redirectTo: '' },
];
