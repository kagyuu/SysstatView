import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/file-search/file-search.component').then((m) => m.FileSearchComponent),
  },
  {
    path: 'graph/:fileId',
    loadComponent: () =>
      import('./pages/graph-view/graph-view.component').then((m) => m.GraphViewComponent),
  },
  { path: '**', redirectTo: '' },
];
