import { Routes } from '@angular/router';
import { unsavedChangesGuard } from './guards/unsaved-changes.guard';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./pages/home/home.component').then(m => m.HomeComponent) },
  { path: 'login', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'register', loadComponent: () => import('./pages/register/register.component').then(m => m.RegisterComponent) },
  { path: 'cards', loadComponent: () => import('./pages/card-list/card-list.component').then(m => m.CardListComponent) },
  { path: 'carpeta', loadComponent: () => import('./pages/carpeta/carpeta.component').then(m => m.CarpetaComponent) },
  { path: 'decks', loadComponent: () => import('./pages/deck-list/deck-list.component').then(m => m.DeckListComponent) },
  { path: 'decks/compare', loadComponent: () => import('./pages/compare-decks/compare-decks.component').then(m => m.CompareDecksComponent) },
  { path: 'decks/:id', loadComponent: () => import('./pages/deck-view/deck-view.component').then(m => m.DeckViewComponent) },
  { path: 'builder', loadComponent: () => import('./pages/format-select/format-select.component').then(m => m.FormatSelectComponent) },
  { path: 'builder/new/:format', loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent), canDeactivate: [unsavedChangesGuard] },
  { path: 'builder/:id', loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent), canDeactivate: [unsavedChangesGuard] },
  { path: 'team', loadComponent: () => import('./pages/team/team.component').then(m => m.TeamComponent) },
  { path: 'profile', loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent) },
  { path: 'profile/edit', loadComponent: () => import('./pages/profile-edit/profile-edit.component').then(m => m.ProfileEditComponent) },
  { path: 'tienda/:token', loadComponent: () => import('./pages/tienda/tienda.component').then(m => m.TiendaComponent) },
  { path: '**', redirectTo: '' },
];
