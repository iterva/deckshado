import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TeamService } from '../../services/team.service';
import { AuthService } from '../../services/auth.service';
import { Team, JoinRequest } from '../../models';

@Component({
  selector: 'app-team',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './team.component.html',
  styleUrl: './team.component.scss',
})
export class TeamComponent implements OnInit {
  // State
  view: 'loading' | 'my-team' | 'browse' = 'loading';
  myTeam: Team | null = null;
  hasTeam = false;
  teams: Team[] = [];
  requests: JoinRequest[] = [];
  isCaptain = false;

  // Create form
  showCreate = false;
  newName = '';
  newDesc = '';

  toast = '';
  toastType: 'success' | 'error' = 'success';

  constructor(
    public auth: AuthService,
    private teamService: TeamService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.loadTeams();
    if (!this.auth.isAuthenticated()) {
      this.view = 'browse';
      return;
    }
    this.teamService.getMyTeam().subscribe({
      next: (team) => {
        this.myTeam = team;
        this.hasTeam = true;
        this.isCaptain = team.my_role === 'captain';
        if (this.isCaptain) this.loadRequests();
        this.view = 'browse';
        this.cdr.detectChanges();
      },
      error: () => {
        this.hasTeam = false;
        this.view = 'browse';
        this.cdr.detectChanges();
      },
    });
  }

  goToMyTeam() {
    this.view = 'my-team';
  }

  goToBrowse() {
    this.view = 'browse';
  }

  loadTeams() {
    this.teamService.getTeams().subscribe({
      next: (data) => {
        this.teams = data.results;
        this.cdr.detectChanges();
      },
    });
  }

  loadRequests() {
    if (!this.myTeam) return;
    this.teamService.getRequests(this.myTeam.id).subscribe({
      next: (r) => { this.requests = r; this.cdr.detectChanges(); },
      error: () => {},
    });
  }

  createTeam() {
    if (!this.newName.trim()) return;
    this.teamService.createTeam({ name: this.newName.trim(), description: this.newDesc.trim() }).subscribe({
      next: () => {
        this.showToast('¡Equipo creado!', 'success');
        this.showCreate = false;
        this.ngOnInit();
      },
      error: (err) => {
        const msg = err.error?.name?.[0] || 'Error al crear equipo';
        this.showToast(msg, 'error');
      },
    });
  }

  requestJoin(teamId: number) {
    this.teamService.requestJoin(teamId).subscribe({
      next: () => this.showToast('Solicitud enviada', 'success'),
      error: (err) => this.showToast(err.error?.error || 'Error', 'error'),
    });
  }

  handleRequest(requestId: number, action: 'accept' | 'reject') {
    this.teamService.handleRequest(requestId, action).subscribe({
      next: () => {
        this.showToast(action === 'accept' ? 'Solicitud aceptada' : 'Solicitud rechazada', 'success');
        this.loadRequests();
        this.teamService.getMyTeam().subscribe(t => {
          this.myTeam = t;
          this.cdr.detectChanges();
        });
      },
      error: (err) => this.showToast(err.error?.error || 'Error', 'error'),
    });
  }

  promote(memberId: number) {
    this.teamService.promoteMember(memberId).subscribe({
      next: () => {
        this.showToast('Promovido a capitán', 'success');
        this.ngOnInit();
      },
      error: (err) => this.showToast(err.error?.error || 'Error', 'error'),
    });
  }

  kick(memberId: number) {
    if (!confirm('¿Expulsar a este miembro?')) return;
    this.teamService.kickMember(memberId).subscribe({
      next: () => {
        this.showToast('Miembro expulsado', 'success');
        this.ngOnInit();
      },
      error: (err) => this.showToast(err.error?.error || 'Error', 'error'),
    });
  }

  leaveTeam() {
    if (!confirm('¿Seguro que quieres salir del equipo?')) return;
    this.teamService.leaveTeam().subscribe({
      next: () => {
        this.showToast('Has salido del equipo', 'success');
        this.myTeam = null;
        this.view = 'browse';
        this.loadTeams();
      },
      error: (err) => this.showToast(err.error?.error || 'Error', 'error'),
    });
  }

  onLogoSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      this.showToast('La imagen no puede pesar más de 2MB', 'error');
      return;
    }
    this.teamService.uploadLogo(file).subscribe({
      next: (res) => {
        if (this.myTeam) this.myTeam.logo_url = res.logo_url;
        this.showToast('Logo actualizado', 'success');
        this.cdr.detectChanges();
      },
      error: (err) => this.showToast(err.error?.error || 'Error al subir logo', 'error'),
    });
  }

  showToast(msg: string, type: 'success' | 'error') {
    this.toast = msg;
    this.toastType = type;
    this.cdr.detectChanges();
    setTimeout(() => { this.toast = ''; this.cdr.detectChanges(); }, 3000);
  }
}
